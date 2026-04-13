"""
AI-Assisted Analyzer

Uses Claude API to provide root cause analysis and remediation suggestions.
Enhanced with PageRank-based context prioritization for cost optimization.
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from anthropic import Anthropic

from api_contract_validator.analysis.context.page_ranker import APIContextRanker
from api_contract_validator.analysis.drift.models import DriftReport
from api_contract_validator.analysis.reasoning.models import (
    AnalysisConfidence,
    AnalysisResult,
    IssueCorrelation,
    RemediationSuggestion,
    RootCauseAnalysis,
)
from api_contract_validator.config.exceptions import AnalysisError
from api_contract_validator.config.logging import get_logger
from api_contract_validator.config.models import AIAnalysisConfig

logger = get_logger("api_contract_validator.analyzer")


class AIAnalyzer:
    """
    AI-assisted analyzer for drift reports using Claude API.
    """

    def __init__(self, config: AIAnalysisConfig):
        """
        Initialize AI analyzer.

        Args:
            config: AI analysis configuration

        Raises:
            AnalysisError: If API key is missing
        """
        self.config = config
        self.context_ranker = APIContextRanker()
        self.api_call_count = 0
        self.tokens_saved = 0

        if not config.enabled:
            logger.info("AI analysis disabled")
            return

        if not config.api_key:
            logger.warning("AI analysis enabled but no API key provided")
            self.client = None
        else:
            try:
                self.client = Anthropic(api_key=config.api_key)
                logger.info(f"AI analyzer initialized with model: {config.model}")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self.client = None

    def analyze_drift(self, drift_report: DriftReport) -> Optional[AnalysisResult]:
        """
        Analyze drift report and generate insights.

        Args:
            drift_report: Drift detection results

        Returns:
            AnalysisResult with AI-generated insights, or None if disabled/failed
        """
        if not self.config.enabled:
            logger.info("AI analysis disabled, skipping")
            return None

        if not self.client:
            logger.warning("AI analysis skipped: no valid API client")
            return None

        if not drift_report.has_issues():
            logger.info("No drift issues to analyze")
            return AnalysisResult(
                executive_summary="No drift issues detected. API conforms to contract specifications.",
                model_used=self.config.model,
                analysis_timestamp=datetime.utcnow().isoformat(),
            )

        logger.info("Starting AI-assisted drift analysis")

        try:
            analysis_result = AnalysisResult(
                model_used=self.config.model,
                analysis_timestamp=datetime.utcnow().isoformat(),
            )

            # Generate executive summary
            analysis_result.executive_summary = self._generate_executive_summary(drift_report)

            # Root cause analysis (if enabled)
            if self.config.enable_root_cause_analysis:
                analysis_result.root_causes = self._analyze_root_causes(drift_report)

            # Remediation suggestions (if enabled)
            if self.config.enable_remediation_suggestions:
                analysis_result.remediations = self._suggest_remediations(drift_report)

            # Issue correlation (if enabled)
            if self.config.enable_correlation_analysis:
                analysis_result.correlations = self._correlate_issues(drift_report)

            # Extract systemic patterns and quick wins
            self._extract_patterns(drift_report, analysis_result)

            logger.info("AI analysis complete")
            return analysis_result

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Graceful degradation - return partial results if any
            return AnalysisResult(
                executive_summary=f"AI analysis partially failed: {str(e)}",
                model_used=self.config.model,
                analysis_timestamp=datetime.utcnow().isoformat(),
            )

    def _generate_executive_summary(self, drift_report: DriftReport) -> str:
        """Generate high-level executive summary."""
        prompt = self._build_executive_summary_prompt(drift_report)

        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=1000,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Failed to generate executive summary: {e}")
            return f"Analysis of {drift_report.summary.total_issues} drift issues across {len(drift_report.summary.affected_endpoints)} endpoints."

    def _analyze_root_causes(self, drift_report: DriftReport) -> List[RootCauseAnalysis]:
        """
        Analyze root causes of drift issues using PageRank-based context prioritization.
        """
        logger.info("Performing root cause analysis with context ranking")
        root_causes = []

        # Organize issues by endpoint
        issues_by_endpoint = self._organize_issues_by_endpoint(drift_report)

        # Get endpoints (if available from drift report metadata)
        endpoints = getattr(drift_report, '_endpoints', [])

        if not endpoints:
            # Fallback to simple endpoint list if metadata not available
            logger.warning("Endpoint metadata not available, using simple ranking")
            ranked_endpoints = list(issues_by_endpoint.keys())[:10]
        else:
            # Use PageRank to prioritize endpoints
            ranked_contexts = self.context_ranker.rank_contexts(
                endpoints=endpoints,
                drift_issues=issues_by_endpoint,
                max_tokens=self.config.max_tokens // 2,  # Reserve half for responses
                max_contexts=10
            )

            # Log ranking explanation
            logger.debug(self.context_ranker.explain_ranking(ranked_contexts))

            ranked_endpoints = [ctx.endpoint_id for ctx in ranked_contexts]

        # Analyze top-ranked endpoints
        for endpoint_id in ranked_endpoints:
            endpoint_issues = issues_by_endpoint.get(endpoint_id, {})
            total_endpoint_issues = sum(len(issues) for issues in endpoint_issues.values())

            if total_endpoint_issues == 0:
                continue

            prompt = self._build_root_cause_prompt(endpoint_id, endpoint_issues)

            try:
                response = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=800,
                    temperature=self.config.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )

                self.api_call_count += 1

                # Parse response and create RootCauseAnalysis
                analysis_text = response.content[0].text.strip()
                root_cause = self._parse_root_cause_response(
                    endpoint_id, analysis_text, endpoint_issues
                )
                if root_cause:
                    root_causes.append(root_cause)

            except Exception as e:
                logger.error(f"Root cause analysis failed for {endpoint_id}: {e}")
                continue

        logger.info(f"Generated {len(root_causes)} root cause analyses ({self.api_call_count} API calls)")
        return root_causes

    def _suggest_remediations(self, drift_report: DriftReport) -> List[RemediationSuggestion]:
        """
        Generate remediation suggestions with batching for cost optimization.
        """
        logger.info("Generating remediation suggestions")
        suggestions = []

        # Focus on high-severity issues first
        high_priority_issues = [
            issue
            for issue in (drift_report.contract_drift + drift_report.validation_drift)
            if issue.severity in ["critical", "high"]
        ]

        # Batch similar issues together
        batched_issues = self._batch_similar_issues(high_priority_issues, max_batches=5)

        logger.info(f"Batched {len(high_priority_issues)} issues into {len(batched_issues)} groups")

        for batch in batched_issues:
            if len(batch) == 1:
                # Single issue - use individual prompt
                prompt = self._build_remediation_prompt(batch[0])
            else:
                # Multiple similar issues - use batch prompt
                prompt = self._build_batch_remediation_prompt(batch)

            try:
                response = self.client.messages.create(
                    model=self.config.model,
                    max_tokens=1500 if len(batch) > 1 else 1000,
                    temperature=self.config.temperature,
                    messages=[{"role": "user", "content": prompt}],
                )

                self.api_call_count += 1

                if len(batch) == 1:
                    suggestion = self._parse_remediation_response(batch[0], response.content[0].text)
                    if suggestion:
                        suggestions.append(suggestion)
                else:
                    batch_suggestions = self._parse_batch_remediation_response(
                        batch, response.content[0].text
                    )
                    suggestions.extend(batch_suggestions)

            except Exception as e:
                logger.error(f"Remediation suggestion failed for batch: {e}")
                continue

        logger.info(f"Generated {len(suggestions)} remediation suggestions ({self.api_call_count} API calls)")
        return suggestions
        return suggestions

    def _correlate_issues(self, drift_report: DriftReport) -> List[IssueCorrelation]:
        """Identify correlations between drift issues."""
        logger.info("Analyzing issue correlations")

        if drift_report.summary.total_issues < 3:
            return []  # Need multiple issues to correlate

        prompt = self._build_correlation_prompt(drift_report)

        try:
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=1500,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            correlations = self._parse_correlation_response(
                response.content[0].text, drift_report
            )
            logger.info(f"Found {len(correlations)} issue correlations")
            return correlations

        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return []

    def _extract_patterns(self, drift_report: DriftReport, analysis_result: AnalysisResult) -> None:
        """Extract systemic patterns and quick wins."""
        # Identify systemic issues
        if drift_report.summary.by_type.get("validation", 0) > 5:
            analysis_result.systemic_issues.append(
                "Widespread validation drift detected across multiple endpoints - "
                "consider reviewing validation middleware"
            )

        if drift_report.summary.by_type.get("contract", 0) > 5:
            analysis_result.systemic_issues.append(
                "Multiple contract drift issues suggest spec-implementation misalignment - "
                "review API specification accuracy"
            )

        # Identify quick wins
        low_severity_count = drift_report.summary.low_count
        if low_severity_count > 0:
            analysis_result.quick_wins.append(
                f"{low_severity_count} low-severity issues that can be addressed quickly"
            )

    # Prompt builders

    def _build_executive_summary_prompt(self, drift_report: DriftReport) -> str:
        """Build prompt for executive summary generation."""
        return f"""Analyze this API drift detection report and provide a concise executive summary (2-3 sentences).

Drift Summary:
- Total Issues: {drift_report.summary.total_issues}
- By Severity: {dict(drift_report.summary.by_severity)}
- By Type: {dict(drift_report.summary.by_type)}
- Affected Endpoints: {len(drift_report.summary.affected_endpoints)}

Focus on:
1. Overall health assessment
2. Most critical concerns
3. Recommended immediate action

Be concise and actionable."""

    def _build_root_cause_prompt(self, endpoint_id: str, endpoint_issues: dict) -> str:
        """Build prompt for root cause analysis."""
        issues_summary = []
        for drift_type, issues in endpoint_issues.items():
            if issues:
                issues_summary.append(f"{drift_type}: {len(issues)} issues")

        return f"""Analyze the root cause of drift issues for endpoint: {endpoint_id}

Issues detected:
{chr(10).join(issues_summary)}

Contract drift examples: {json.dumps([{'field': i.field_path, 'expected': str(i.expected)[:50], 'actual': str(i.actual)[:50]} for i in endpoint_issues.get('contract', [])[:3]], indent=2)}

Provide:
1. Primary hypothesis for why these issues occurred
2. 2-3 contributing factors
3. Evidence supporting your hypothesis

Be specific and technical."""

    def _build_remediation_prompt(self, issue) -> str:
        """Build prompt for remediation suggestion."""
        return f"""Suggest how to fix this API drift issue:

Endpoint: {issue.endpoint_id}
Issue: {issue.message}
Severity: {issue.severity}

Provide:
1. Clear fix title
2. Detailed explanation
3. Code example (if applicable)
4. 3-5 implementation steps
5. Effort estimate (low/medium/high)

Be practical and specific."""

    def _build_correlation_prompt(self, drift_report: DriftReport) -> str:
        """Build prompt for correlation analysis."""
        return f"""Identify correlations between these API drift issues:

Total Issues: {drift_report.summary.total_issues}
Affected Endpoints: {', '.join(drift_report.summary.affected_endpoints[:10])}

Contract Drift: {len(drift_report.contract_drift)} issues
Validation Drift: {len(drift_report.validation_drift)} issues
Behavioral Drift: {len(drift_report.behavioral_drift)} issues

Look for:
1. Shared root causes across endpoints
2. Cascading failures
3. Common patterns

Provide 1-3 significant correlations."""

    # Response parsers

    def _parse_root_cause_response(
        self, endpoint_id: str, response_text: str, endpoint_issues: dict
    ) -> Optional[RootCauseAnalysis]:
        """Parse root cause analysis from AI response."""
        # Extract issue IDs
        issue_ids = []
        for issues_list in endpoint_issues.values():
            issue_ids.extend([i.test_id for i in issues_list[:3]])

        return RootCauseAnalysis(
            issue_id=f"rc-{endpoint_id}",
            endpoint_id=endpoint_id,
            hypothesis=response_text.split("\n\n")[0] if response_text else "Analysis pending",
            contributing_factors=self._extract_bullet_points(response_text),
            confidence=AnalysisConfidence.MEDIUM,
            evidence_references=issue_ids,
        )

    def _parse_remediation_response(
        self, issue, response_text: str
    ) -> Optional[RemediationSuggestion]:
        """Parse remediation suggestion from AI response."""
        lines = response_text.split("\n")
        title = lines[0] if lines else "Fix drift issue"

        # Extract code blocks if present
        code_example = None
        if "```" in response_text:
            code_blocks = response_text.split("```")
            if len(code_blocks) >= 3:
                code_example = code_blocks[1].strip()

        steps = self._extract_bullet_points(response_text)

        return RemediationSuggestion(
            issue_id=issue.test_id,
            endpoint_id=issue.endpoint_id,
            title=title[:100],
            description=response_text[:500],
            code_example=code_example,
            implementation_steps=steps[:5],
            estimated_effort="medium",
            priority=issue.severity if hasattr(issue, "severity") else "medium",
        )

    def _parse_correlation_response(
        self, response_text: str, drift_report: DriftReport
    ) -> List[IssueCorrelation]:
        """Parse correlation analysis from AI response."""
        # Simple parsing - in production you'd use more sophisticated extraction
        correlations = []

        # Look for patterns in the response
        if "validation" in response_text.lower() and len(drift_report.validation_drift) > 3:
            issue_ids = [i.test_id for i in drift_report.validation_drift[:5]]
            endpoints = list(set(i.endpoint_id for i in drift_report.validation_drift))[:5]

            correlations.append(
                IssueCorrelation(
                    issue_ids=issue_ids,
                    endpoints=endpoints,
                    correlation_type="pattern",
                    description="Multiple validation drift issues across endpoints suggest systematic validation gaps",
                    impact_summary="API may have weak input validation across multiple endpoints",
                )
            )

        return correlations

    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points or numbered items from text."""
        lines = text.split("\n")
        points = []

        for line in lines:
            stripped = line.strip()
            # Look for bullets (-, *, •) or numbers (1., 2.)
            if stripped and (
                stripped.startswith(("-", "*", "•"))
                or (len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in [".", ")"])
            ):
                # Remove bullet/number prefix
                clean = stripped.lstrip("-*•").lstrip()
                if clean and len(clean) > 1 and clean[0].isdigit():
                    clean = clean[2:].lstrip()
                if clean:
                    points.append(clean)

        return points[:10]  # Limit to 10 points

    def _organize_issues_by_endpoint(self, drift_report: DriftReport) -> Dict[str, Dict[str, List]]:
        """
        Organize all drift issues by endpoint.

        Returns:
            Dict mapping endpoint_id to dict of issue types and their lists
        """
        issues_by_endpoint = defaultdict(lambda: defaultdict(list))

        for issue in drift_report.contract_drift:
            issues_by_endpoint[issue.endpoint_id]['contract'].append(issue)

        for issue in drift_report.validation_drift:
            issues_by_endpoint[issue.endpoint_id]['validation'].append(issue)

        for issue in drift_report.behavioral_drift:
            issues_by_endpoint[issue.endpoint_id]['behavioral'].append(issue)

        return dict(issues_by_endpoint)

    def _batch_similar_issues(self, issues: List, max_batches: int = 5) -> List[List]:
        """
        Batch similar issues together for efficient API calls.

        Groups issues by:
        - Same endpoint
        - Same issue type
        - Similar error patterns
        """
        batches = defaultdict(list)

        for issue in issues:
            # Create batch key from endpoint and issue type
            batch_key = (
                issue.endpoint_id,
                type(issue).__name__,
                getattr(issue, 'severity', 'medium')
            )
            batches[batch_key].append(issue)

        # Sort batches by size (largest first) and severity
        sorted_batches = sorted(
            batches.values(),
            key=lambda b: (
                self._batch_priority_score(b),
                len(b)
            ),
            reverse=True
        )

        return sorted_batches[:max_batches]

    def _batch_priority_score(self, batch: List) -> float:
        """Calculate priority score for a batch of issues."""
        severity_weights = {'critical': 10, 'high': 5, 'medium': 2, 'low': 1}
        total = sum(
            severity_weights.get(getattr(issue, 'severity', 'medium'), 1)
            for issue in batch
        )
        return total / len(batch) if batch else 0

    def _build_batch_remediation_prompt(self, issues: List) -> str:
        """Build prompt for batch remediation of similar issues."""
        endpoint_id = issues[0].endpoint_id
        issue_type = type(issues[0]).__name__

        issues_summary = "\n".join([
            f"  - {getattr(issue, 'message', str(issue))[:100]}"
            for issue in issues[:5]  # Max 5 examples
        ])

        return f"""Suggest how to fix these {len(issues)} similar API drift issues:

Endpoint: {endpoint_id}
Issue Type: {issue_type}
Severity: {getattr(issues[0], 'severity', 'medium')}

Issues:
{issues_summary}

Provide ONE remediation that fixes all these issues:
1. Clear fix title
2. Root cause explanation
3. Code example that addresses the pattern
4. 3-5 implementation steps
5. Effort estimate (low/medium/high)

Be practical and focus on the systematic fix."""

    def _parse_batch_remediation_response(
        self, issues: List, response_text: str
    ) -> List[RemediationSuggestion]:
        """Parse batch remediation response into individual suggestions."""
        lines = response_text.split("\n")
        title = lines[0] if lines else "Fix batch of similar issues"

        # Extract code blocks if present
        code_example = None
        if "```" in response_text:
            code_blocks = response_text.split("```")
            if len(code_blocks) >= 3:
                code_example = code_blocks[1].strip()

        steps = self._extract_bullet_points(response_text)

        # Create one suggestion that applies to all issues in batch
        suggestion = RemediationSuggestion(
            issue_id=f"batch-{issues[0].endpoint_id}",
            endpoint_id=issues[0].endpoint_id,
            title=f"{title} ({len(issues)} issues)",
            description=f"Batch fix for {len(issues)} similar issues:\n{response_text[:300]}...",
            code_example=code_example,
            implementation_steps=steps[:5],
            estimated_effort="medium",
            priority=getattr(issues[0], 'severity', 'medium'),
        )

        return [suggestion]
