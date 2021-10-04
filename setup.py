import os
import setuptools

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

setuptools.setup(name="open-data-linter",
                 version="0.1.1",
                 author="yusk,shiita0903,IidaTakuma",
                 description="Open Data Linter",
                 long_description=README,
                 long_description_content_type="text/markdown",
                 packages=setuptools.find_packages(),
                 license='MIT License',
                 classifiers=[
                     "Programming Language :: Python :: 3",
                     "Programming Language :: Python :: 3.6",
                     "License :: OSI Approved :: MIT License",
                 ])
