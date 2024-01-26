from setuptools import setup

setup(
    name='paraterra',
    version='0.1.0',
    py_modules=['paraterra'],
    install_requires=[
        'Click',
        'click-option-group',
        'tabulate'
    ],
    entry_points={
        'console_scripts': [
            'paraterra = paraterra:cli',
        ],
    },
)