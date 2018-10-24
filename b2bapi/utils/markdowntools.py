import markdown

def parse_markdown(text):
    try:
        return markdown.markdown(
                text,
                extensions=[
                    'footnotes', 
                    'def_list', 
                    'attr_list', 
                    'sane_lists',
                    'smarty'], 
                output_format="html5")
    except:
        pass
    return text

