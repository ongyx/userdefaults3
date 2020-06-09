import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="userdefaults3",
    version="1.1.3",
    author="Ong Yong Xin",
    author_email="ongyongxin.offical@gmail.com",
    description="Python 3 rewrite of userdefaults, a pure-Python interface to NSUserDefaults.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/onyxware/userdefaults3",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    py_modules=["userdefaults3"],
    python_requires='>=3.7',
    install_requires=[
        "rubicon-objc",
    ],
)
