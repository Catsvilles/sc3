
import setuptools


with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='sc3',
    version='0.7.0',
    author='Lucas Samaruga',
    author_email='samarugalucas@gmail.com',
    license='GPLv3',
    platforms='Any',
    description='SuperCollider 3 class library Python 3 port',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/smrg-lm/sc3',
    packages=[
        'sc3', 'sc3.base',
        'sc3.seq', 'sc3.seq.patterns',
        'sc3.synth', 'sc3.synth.ugens'
    ],
    python_requires='>=3.6',
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha'
    ],
    keywords='SuperCollider sound synthesis music composition'
)
