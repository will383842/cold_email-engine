"""Template Renderer - Render email templates with variables."""

from typing import Dict, Any
from jinja2 import Template, TemplateSyntaxError, UndefinedError


class TemplateRenderer:
    """
    Render email templates using Jinja2.

    Supports variables, filters, and basic logic.
    """

    def render(
        self,
        template_content: str,
        variables: Dict[str, Any],
        strict: bool = False
    ) -> str:
        """
        Render template with variables.

        Args:
            template_content: Template HTML/text content with Jinja2 syntax
            variables: Dict of variables to substitute
            strict: If True, raise error on undefined variables. If False, replace with empty string.

        Returns:
            Rendered content

        Raises:
            TemplateSyntaxError: If template syntax is invalid
            UndefinedError: If variable is undefined and strict=True

        Example:
            renderer = TemplateRenderer()

            template = '''
            <html>
            <body>
                <h1>Hello {{ first_name }}!</h1>
                <p>Your email is {{ email }}</p>
            </body>
            </html>
            '''

            variables = {
                "first_name": "Jean",
                "email": "jean@example.com"
            }

            result = renderer.render(template, variables)
        """
        try:
            # Create Jinja2 template
            if strict:
                template = Template(template_content)
            else:
                # Undefined variables become empty strings
                template = Template(template_content, undefined=SilentUndefined)

            # Render with variables
            return template.render(**variables)

        except TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error at line {e.lineno}: {e.message}")
        except UndefinedError as e:
            raise ValueError(f"Undefined variable in template: {str(e)}")

    def render_subject(
        self,
        subject_template: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        Render email subject with variables.

        Same as render() but strips whitespace.

        Args:
            subject_template: Subject line with variables
            variables: Dict of variables

        Returns:
            Rendered subject (stripped)

        Example:
            subject = renderer.render_subject(
                "Hello {{ first_name }} - Special offer!",
                {"first_name": "Jean"}
            )
            # Returns: "Hello Jean - Special offer!"
        """
        rendered = self.render(subject_template, variables, strict=False)
        return rendered.strip()

    def get_template_variables(self, template_content: str) -> list[str]:
        """
        Extract all variables from template.

        Args:
            template_content: Template content

        Returns:
            List of variable names found in template

        Example:
            template = "Hello {{ first_name }}! Email: {{ email }}"
            variables = renderer.get_template_variables(template)
            # Returns: ["first_name", "email"]
        """
        try:
            template = Template(template_content)
            # Get undeclared variables
            from jinja2.meta import find_undeclared_variables
            from jinja2 import Environment

            env = Environment()
            ast = env.parse(template_content)
            variables = find_undeclared_variables(ast)

            return sorted(list(variables))

        except Exception:
            return []

    def validate_template(self, template_content: str) -> tuple[bool, str]:
        """
        Validate template syntax.

        Args:
            template_content: Template content

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if template is valid
            - error_message: Empty string if valid, error message if invalid

        Example:
            valid, error = renderer.validate_template("Hello {{ first_name }}")
            if not valid:
                print(f"Template error: {error}")
        """
        try:
            Template(template_content)
            return True, ""
        except TemplateSyntaxError as e:
            return False, f"Syntax error at line {e.lineno}: {e.message}"
        except Exception as e:
            return False, str(e)

    def render_preview(
        self,
        template_content: str,
        sample_variables: Dict[str, Any] | None = None
    ) -> str:
        """
        Render template preview with sample data.

        Args:
            template_content: Template content
            sample_variables: Optional sample variables. If not provided, uses defaults.

        Returns:
            Rendered preview

        Example:
            preview = renderer.render_preview(
                "Hello {{ first_name }}!",
                {"first_name": "Jean"}
            )
        """
        if sample_variables is None:
            # Default sample variables
            sample_variables = {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "company": "ACME Corp",
                "phone": "+33 1 23 45 67 89",
            }

        return self.render(template_content, sample_variables, strict=False)


class SilentUndefined:
    """
    Jinja2 Undefined class that returns empty string for undefined variables.

    This prevents errors when variables are missing.
    """

    def __init__(self, *args, **kwargs):
        pass

    def __str__(self):
        return ""

    def __repr__(self):
        return ""

    def __bool__(self):
        return False

    def __getattr__(self, name):
        return self

    def __getitem__(self, key):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __iter__(self):
        return iter([])
