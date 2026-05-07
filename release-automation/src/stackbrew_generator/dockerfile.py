"""Dockerfile template rendering using Jinja2."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, ValidationError


class DockerfileContext(BaseModel):
    """Available context variables for Dockerfile templates.

    Attributes:
        custom_build: Whether this is a custom build
        redis_download_url: Redis source tarball download URL (required)
        redis_download_sha: Redis source tarball SHA256 checksum (required)
    """
    release_tag: str = ""
    custom_build: bool = False
    redis_download_url: str = ""
    redis_download_sha: str = ""


class DockerfileRenderer:
    """Render Dockerfile templates using Jinja2."""

    def __init__(self):
        """Initialize the Dockerfile renderer."""
        self.context = DockerfileContext()

    def set_variable(self, name: str, value: Any) -> None:
        """Set a context variable.

        Args:
            name: Variable name
            value: Variable value (will be converted to appropriate type)

        Raises:
            ValueError: If variable name is not recognized or value is invalid
        """
        # Check if field exists in the model
        if name not in DockerfileContext.model_fields:
            valid_fields = ', '.join(DockerfileContext.model_fields.keys())
            raise ValueError(f"Unknown context variable: {name}. Valid variables: {valid_fields}")

        # Use Pydantic's validation to convert and validate the value
        try:
            # Create a new context with the updated value
            updated_data = self.context.model_dump()
            updated_data[name] = value
            self.context = DockerfileContext(**updated_data)
        except ValidationError as e:
            # Extract the error message for this field
            error_msg = e.errors()[0]['msg']
            raise ValueError(f"Invalid value for {name}: {error_msg}")

    def render_template(self, template_path: Path) -> str:
        """Render a Dockerfile template.

        Args:
            template_path: Path to the Jinja2 template file

        Returns:
            Rendered Dockerfile content

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        # Set up Jinja2 environment
        template_dir = template_path.parent
        template_name = template_path.name

        env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=StrictUndefined,
        )

        # Add custom 'required' filter (like Ansible)
        def required_filter(value, msg=None):
            """Raise an error if the value is undefined or empty.

            Usage in template:
                {{ variable_name | required }}
                {{ variable_name | required("Custom error message") }}
            """
            if value is None or value == "" or (isinstance(value, str) and not value.strip()):
                error_msg = msg or "Required variable is not defined or is empty"
                raise ValueError(error_msg)
            return value

        env.filters['required'] = required_filter

        # Load and render template
        template = env.get_template(template_name)
        return template.render(**self.context.model_dump())

