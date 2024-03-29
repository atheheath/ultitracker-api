from setuptools import setup

with open("./requirements.txt", "r") as f:
    packages = [x.strip() for x in f.readlines()]

setup(
    name="UltitrackerAPI",
    version="2021.09.11",
    packages=["ultitrackerapi",],
    license="Creative Commons Attribution-Noncommercial-Share Alike license",
    # long_description=open('README.txt').read(),
    install_requires=packages,
)
