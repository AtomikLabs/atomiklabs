from setuptools import setup, find_packages

setup(
    name="shared",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "psycopg2-binary>=2.9.9"
    ],
    python_requires=">=3.11",
)
