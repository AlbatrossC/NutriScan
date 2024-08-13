from django import template
import re

register = template.Library()

@register.filter
def bold(value):
    """
    Replaces '**text**' with '<strong>text</strong>'.
    """
    return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', value)

@register.filter
def format_response(value):
    """
    Converts markdown-like syntax to HTML:
    - '## Title' to <h2>Title</h2>
    - '**text**' to <strong>text</strong>
    - '*text*' to <em>text</em>
    - '| Header 1 | Header 2 |' to table headers
    - '| Cell 1 | Cell 2 |' to table rows
    - Double new lines to <p> (paragraphs)
    """
    # Convert titles
    value = re.sub(r'##\s*(.+)', r'<h2>\1</h2>', value)
    
    # Convert bold text
    value = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', value)
    
    # Convert italic text
    value = re.sub(r'\*(.*?)\*', r'<em>\1</em>', value)

    # Convert table headers
    value = re.sub(r'^\|(.+?)\|\s*$', r'<thead><tr><th>\1</th></tr></thead><tbody>', value, flags=re.MULTILINE)
    
    # Convert table rows
    value = re.sub(r'^\|(.+?)\|\s*$', r'<tr><td>\1</td></tr>', value, flags=re.MULTILINE)
    
    # Handle table cells
    value = re.sub(r'\|\s*(.*?)\s*\|', r'</td><td>\1</td>', value)

    # Close table body
    value = re.sub(r'(<tr><td>.+</td></tr>)', r'\1</tbody>', value)

    # Convert double newlines to <p>
    value = re.sub(r'\n\n+', r'</p><p>', value)
    
    # Wrap the whole text in <p> tags if it starts with text
    value = f'<p>{value}</p>'
    
    return value
