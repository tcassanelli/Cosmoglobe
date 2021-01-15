import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cosmoglobe", # Replace with your own username
    version="0.0.1",
    author="Metin San",
    author_email="metinisan@gmail.com",
    description="The Cosmoglobe Sky Model",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cosmoglobe",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "healpy",
        "astropy",
        "numpy",
        "numba",
        "h5py",
    ]
)