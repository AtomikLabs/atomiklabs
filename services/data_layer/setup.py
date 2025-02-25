from setuptools import setup, find_packages

setup(
    name="atomiklabs-data",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.5",
        "boto3>=1.26.0",
        "alembic>=1.10.0",
    ],
    entry_points={
        "console_scripts": [
            "init-db=src.init_db:main",
            "db-migrate=src.migration:main",
        ],
    },
    python_requires=">=3.8",
    description="Data access layer for AtomikLabs research data system",
    author="AtomikLabs",
) 