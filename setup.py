import setuptools

setuptools.setup(
    name="asmde",
    version="0.1.0",
    author="Nicolas Brunie",
    author_email="nibrunie@gmail.com",
    description="a small toolset for assembly-level development",
    url="https://github.com/nibrunie/asmde",
    packages=setuptools.find_packages(),
    #package_dir={"": "asmde"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[],
    python_requires='>=3.5',
)
