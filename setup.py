import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="userdefaults",
    version="1.0.0",
    author="Ong Yong Xin",
    author_email="ongyongxin.offical@gmail.com",
    description="Python interface to NSUserDefaults, using Objective-C",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/onyxware/userdefaults",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    py_modules=["userdefaults"],
    python_requires='>=3.7',
    install_requires=[
        "rubicon-objc",
    ],
)
