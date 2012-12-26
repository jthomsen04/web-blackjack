import jinja2
import webapp2

from main import template_dir

# Initialize the jinja2 environment
jinja_environment = jinja2.Environment(autoescape=True,
        loader=jinja2.FileSystemLoader(template_dir))

class AppHandler(webapp2.RequestHandler):
    """Base handler, encapsulating jinja2 functions."""

    def __init__(self, request=None, response=None):
        """Initialize the handler."""
        super(AppHandler, self).__init__(request, response)
        self.jinja = jinja_environment

    def write(self, string):
        """Write an arbitrary string to the response stream."""
        self.response.out.write(string)

    def render_str(self, template_name, values=None, **kwargs):
        """Render a jinja2 template and return it as a string."""
        template = self.jinja.get_template(template_name)
        return template.render(values or kwargs)

    def render(self, template_name, values=None, **kwargs):
        """Render a jinja2 template using a dictionary or keyword arguments."""
        self.write(self.render_str(template_name, values or kwargs))

    def redirect_to(self, name, *args, **kwargs):
        """Redirect to a URI that corresponds to a route name."""
        self.redirect(self.uri_for(name, *args, **kwargs))