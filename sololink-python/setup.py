from setuptools import setup, Extension
import platform

version = '1.3.0'

setup(name='sololink',
      zip_safe=True,
      version=version,
      description='Python interface for SoloLink',
      long_description='Python interface for SoloLink',
      url='https://github.com/3drobotics/sololink-python',
      author='3D Robotics',
      install_requires=[
          'posix_ipc',
      ],
      author_email='will.silva@3drobotics.com, jfinley@3drobotics.com,',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 2.7',
          'Topic :: Scientific/Engineering',
      ],
      packages=[
          'sololink'
      ],
      ext_modules=[])
