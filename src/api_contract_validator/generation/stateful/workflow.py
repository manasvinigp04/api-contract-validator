"""Workflow-based test generation."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from api_contract_validator.config.logging import get_logger
from api_contract_validator.generation.base import TestCase, TestCaseType, BaseTestGenerator
from api_contract_validator.generation.stateful.dependency import DependencyGraphBuilder
from api_contract_validator.generation.valid.generator import ValidTestGenerator
from api_contract_validator.input.normalizer.models import UnifiedAPISpec, Endpoint, HTTPMethod

logger = get_logger(__name__)


@dataclass
class WorkflowStep:
    """Single step in a workflow."""
    endpoint: Endpoint
    depends_on: Optional[str] = None  # Previous step's endpoint_id
    extract_from_previous: Optional[str] = None  # Field to extract (e.g., "id")
    inject_into: Optional[str] = None  # Field to inject into (e.g., "user_id")


class WorkflowChain:
    """Represents a multi-step API workflow."""

    def __init__(self, name: str, steps: List[WorkflowStep]):
        self.name = name
        self.steps = steps

    def to_test_case(self, test_id: str) -> 'WorkflowTestCase':
        """Convert workflow to test case."""
        return WorkflowTestCase(
            test_id=test_id,
            workflow_name=self.name,
            steps=self.steps
        )


class WorkflowTestCase(TestCase):
    """Test case that executes multiple API calls in sequence."""

    def __init__(self, test_id: str, workflow_name: str, steps: List[WorkflowStep], **kwargs):
        first_step = steps[0] if steps else None
        super().__init__(
            test_id=test_id,
            endpoint=first_step.endpoint if first_step else None,
            test_type=TestCaseType.VALID,
            description=f"Workflow: {workflow_name}",
            method=first_step.endpoint.method if first_step else HTTPMethod.GET,
            path=first_step.endpoint.path if first_step else "/",
            should_pass=True,
            priority=1.6,  # Workflows are high priority
            **kwargs
        )
        self.workflow_name = workflow_name
        self.workflow_steps = steps


class WorkflowGenerator(BaseTestGenerator):
    """Generates stateful workflow tests."""

    def __init__(self, spec: UnifiedAPISpec):
        super().__init__()
        self.spec = spec
        self.dependency_builder = DependencyGraphBuilder(spec)
        self.valid_generator = ValidTestGenerator()

    def generate_workflows(self) -> List[WorkflowChain]:
        """Generate workflow chains from API spec."""
        logger.info("Building endpoint dependency graph...")
        self.dependency_builder.build_graph()

        workflow_chains = self.dependency_builder.get_workflow_chains()
        logger.info(f"Found {len(workflow_chains)} potential workflow chains")

        workflows = []
        for chain_ids in workflow_chains:
            workflow = self._build_workflow(chain_ids)
            if workflow:
                workflows.append(workflow)

        return workflows

    def _build_workflow(self, endpoint_ids: List[str]) -> Optional[WorkflowChain]:
        """Build workflow from endpoint IDs."""
        endpoints = [next((e for e in self.spec.endpoints if e.endpoint_id == eid), None)
                    for eid in endpoint_ids]
        endpoints = [e for e in endpoints if e is not None]

        if len(endpoints) < 2:
            return None

        steps = []
        for i, endpoint in enumerate(endpoints):
            step = WorkflowStep(
                endpoint=endpoint,
                depends_on=endpoints[i-1].endpoint_id if i > 0 else None,
                extract_from_previous="id" if i > 0 and endpoint.method != HTTPMethod.POST else None,
                inject_into=self._find_id_param(endpoint) if i > 0 else None
            )
            steps.append(step)

        resource = self.dependency_builder._extract_resource(endpoints[0].path)
        workflow_name = f"{resource}_crud_workflow"

        return WorkflowChain(name=workflow_name, steps=steps)

    def _find_id_param(self, endpoint: Endpoint) -> Optional[str]:
        """Find ID parameter in endpoint path."""
        if '{id}' in endpoint.path:
            return 'id'
        for param in endpoint.parameters:
            if 'id' in param.name.lower():
                return param.name
        return None

    def generate_tests(self, endpoint: Endpoint = None) -> List[TestCase]:
        """Generate workflow test cases."""
        workflows = self.generate_workflows()
        tests = []

        for workflow in workflows:
            test = workflow.to_test_case(
                test_id=self.generate_test_id(f"workflow_{workflow.name}")
            )
            tests.append(test)

        logger.info(f"Generated {len(tests)} workflow tests")
        return tests
