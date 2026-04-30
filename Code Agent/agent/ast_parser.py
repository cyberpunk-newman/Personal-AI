from tree_sitter_languages import get_language, get_parser

LANGUAGE = get_language("python")
parser = get_parser("python")

def extract_functions(code: str):
    tree = parser.parse(bytes(code, "utf8"))
    root = tree.root_node

    functions = []

    def traverse(node):
        if node.type == "function_definition":
            name = node.child_by_field_name("name").text.decode()
            functions.append({
                "name": name,
                "code": node.text.decode()
            })
        for child in node.children:
            traverse(child)

    traverse(root)
    return functions