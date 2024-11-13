import re
import sys
import shutil
import os
import yaml
from jsonschema import validate, ValidationError
from jinja2 import Environment, FileSystemLoader
from git import Repo, GitCommandError

DOCS_REPO_NAME = "mtasa-wiki"
DOCS_REPO_URL = f"https://github.com/multitheftauto/{DOCS_REPO_NAME}.git"
DOCS_REPO_PATH = f"./input/{DOCS_REPO_NAME}/"

OUTPUT_TEMPLATES_PATH = "./output/templates/"
OUTPUT_HTML_PATH = "./output/html/"

def clone_or_pull_repo(repo_url, destination_path):
    repoName = f"multitheftauto/{DOCS_REPO_NAME}"
    if os.path.exists(destination_path):
        try:
            repo = Repo(destination_path)
            repo.git.pull()
            print(f"Repository {repoName} pulled successfully.")
        except GitCommandError as e:
            print(f"Error pulling repository {repoName}: {e}")
    else:
        Repo.clone_from(repo_url, destination_path)
        print(f"Repository {repoName} cloned successfully.")

def load_schema(schema_path):
    with open(schema_path, 'r') as file:
        schema = yaml.safe_load(file)
    return schema

def load_and_validate_yaml(file_path, schema):
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
        try:
            validate(instance=data, schema=schema)
            return data
        except ValidationError as e:
            print(f"Validation error in {file_path}: {e.message}")
            return None

def load_all_functions(doc_folder, schema):
    functions = []
    for root, _, files in os.walk(doc_folder):
        for filename in files:
            if filename.endswith('.yaml'):
                file_path = os.path.join(root, filename)
                function_data = load_and_validate_yaml(file_path, schema)
                if function_data:
                    function_data['path'] = file_path
                    functions.append(function_data)
    return functions

def get_function_def(function):
    return function.get('shared') or function.get('client') or function.get('server')

def get_function_name(function):
    return get_function_def(function).get('name')

def get_function_examples(function):
    examples = []
    for example in get_function_def(function).get('examples', []):
        example_path = os.path.join(os.path.dirname(function.get('path')), example.get('path'))
        with open(example_path, 'r') as file:
            example_code = file.read()
        examples.append({
            'path': example.get('path'),
            'description': example.get('description'),
            'code': example_code
        })
    return examples

def generate_html_files(functions, output_folder):
    env = Environment(loader=FileSystemLoader('.'))
    template_path = os.path.join(OUTPUT_TEMPLATES_PATH, 'function.html')
    template = env.get_template(template_path)
    
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)
    for function in functions:
        function_name = get_function_name(function)
        html_content = template.render(
            function=function,
            function_name=function_name,
            function_examples=get_function_examples(function)
        )

        # Transform any text surrounded by [[ ]] into <a> links
        html_content = re.sub(r'\[\[(.*?)\]\]', r'<a href="\1.html">\1</a>', html_content)

        output_path = os.path.join(output_folder, f"{function_name}.html")
        with open(output_path, 'w') as html_file:
            html_file.write(html_content)
        print(f"Generated {output_path}")

def parse_functions():
    function_schema = load_schema(DOCS_REPO_PATH+'schemas/function.yaml')
    functions = load_all_functions(DOCS_REPO_PATH+'functions/', function_schema)

    generate_html_files(functions, OUTPUT_HTML_PATH)

def run():
    clone_or_pull_repo(DOCS_REPO_URL, DOCS_REPO_PATH)
    parse_functions()

if __name__ == '__main__':
    run()
