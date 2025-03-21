from setuptools import setup, find_namespace_packages

setup(
    name="atomiklabs-neo4j-client",
    version="0.1.0",
    description="Neo4j client",
    author="Brad Edwards",
    author_email="j.bradley.edwards@gmail.com",
    packages=find_namespace_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "neo4j>=5.28.1,<6.0.0",
        "python-dotenv>=1.0.0"
    ],
    python_requires=">=3.11",
    readme="README.md",
) 