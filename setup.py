import setuptools

setuptools.setup(
    name="asmde",
    version="0.1.0",
    author="Nicolas Brunie",
    author_email="nibrunie@gmail.com",
    description="a small toolset for assembly-level development",
    url="https://github.com/nibrunie/asmde",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=["asmde", "asmde_arch"],
    package_dir={"asmde": "asmde", "asmde_arch": "asmde_arch"},
    install_requires=[],
    python_requires='>=3.5',
)
