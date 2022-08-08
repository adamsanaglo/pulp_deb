from setuptools import setup

setup(
    name="pmcstatus",
    python_requires=">=3.8",
    description="CLI with helpful tools for managing the PMC status site.",
    version="0.0.1",
    install_requires=[
        "click",
        "requests"
    ],
    py_modules=['pmcstatus'],
    entry_points={
        'console_scripts': [
            'pmcstatus = pmcstatus:main',
        ]
    },
)
