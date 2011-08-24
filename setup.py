#!/usr/bin/env python

# The current version of the system.  Format is #.#.#[-DEV].
version = '0.0.3-DEV'

import distutils.sysconfig

# Require Python 2.4 or higher, but not 3.x
#py_ver = distutils.sysconfig.get_python_version()
#if (py_ver < '2.4') or (py_ver >= '3.0'):
#    raise ValueError('PyXB requires Python version 2.x where x >= 4 (you have %s)' % (py_ver,))

import os
import stat
import re

from distutils.core import setup, Command

# Stupid little command to automatically update the version number
# where it needs to be updated.
class update_version (Command):
    # Brief (40-50 characters) description of the command
    description = "Substitute @VERSION@ in relevant files"

    # List of option tuples: long name, short name (None if no short
    # name), and help string.
    user_options = [ ]
    boolean_options = [ ]

    # Files in the distribution that need to be rewritten when the
    # version number changes
    files = ( 'README.txt', 'coapy/__init__.py', 'doc/conf.py' )

    # The substitutions (key braced by @ signs)
    substitutions = { 'VERSION' : version,
                      'SHORTVERSION' : '.'.join(version.split('.')[:2]) }

    def initialize_options (self):
        pass

    def finalize_options (self):
        pass

    def run (self):
        for f in self.files:
            text = file('%s.in' % (f,)).read()
            for (k, v) in self.substitutions.items():
                text = text.replace('@%s@' % (k,), v)
            file(f,'w').write(text)

class test (Command):

    # Brief (40-50 characters) description of the command
    description = "Run all unit tests found in testdirs"

    # List of option tuples: long name, short name (None if no short
    # name), and help string.
    user_options = [ ( 'testdirs=', None, 'colon separated list of directories to search for tests' ),
                     ( 'trace-tests', 'v', 'trace search for tests' ),
                     ( 'inhibit-output', 'q', 'inhibit test output' ),
                     ]
    boolean_options = [ 'trace-tests', 'inhibit-output' ]

    def initialize_options (self):
        self.trace_tests = None
        self.inhibit_output = None
        self.testdirs = 'unittests'

    def finalize_options (self):
        pass

    # Regular expression that matches unittest sources
    __TestFile_re = re.compile('^test.*\.py$')

    def run (self):
        # Walk the tests hierarchy looking for tests
        dirs = self.testdirs.split(':')
        tests = [ ]
        while dirs:
            dir = dirs.pop(0)
            if self.trace_tests:
                print 'Searching for tests in %s' % (dir,)
            for f in os.listdir(dir):
                fn = os.path.join(dir, f)
                statb = os.stat(fn)
                if stat.S_ISDIR(statb[0]):
                    dirs.append(fn)
                elif self.__TestFile_re.match(f):
                    tests.append(fn)

        number = 0
        import sys
        import traceback
        import new
        import unittest
        import types

        # Import each test into its own module, then add the test
        # cases in it to a complete suite.
        loader = unittest.defaultTestLoader
        suite = unittest.TestSuite()
        used_names = set()
        for fn in tests:
            stage = 'compile'
            try:
                # Assign a unique name for this test
                test_name = os.path.basename(fn).split('.')[0]
                test_name = test_name.replace('-', '_')
                number = 2
                base_name = test_name
                while test_name in used_names:
                    test_name = '%s%d' % (base_name, number)
                    number += 1

                # Read the test source in and compile it
                rv = compile(file(fn).read(), test_name, 'exec')
                state = 'evaluate'

                # Make a copy of the globals array so we don't
                # contaminate this environment.
                g = globals().copy()

                # The test cases use __file__ to determine the path to
                # the schemas
                g['__file__'] = fn

                # Create a module into which the test will be evaluated.
                module = new.module(test_name)

                # The generated code uses __name__ to look up the
                # containing module in sys.modules.
                g['__name__'] = test_name
                sys.modules[test_name] = module

                # Import the test into the module, making sure the created globals look like they're in the module.
                eval(rv, g)
                module.__dict__.update(g)

                # Find all subclasses of unittest.TestCase that were
                # in the test source and add them to the suite.
                for (nm, obj) in g.items():
                    if (type == type(obj)) and issubclass(obj, unittest.TestCase):
                        suite.addTest(loader.loadTestsFromTestCase(obj))
                if self.trace_tests:
                    print '%s imported' % (fn,)
            except Exception, e:
                print '%s failed in %s: %s' % (fn, stage, e)
                raise

        # Run everything
        verbosity = 1
        if self.trace_tests:
            verbosity = 2
        elif self.inhibit_output:
            # Don't know how to do this for real
            verbosity = 0
        runner = unittest.TextTestRunner(verbosity=verbosity)
        runner.run(suite)

import glob
import sys

packages = [
        'coapy'
        ]
package_data = {}

setup(name='CoAPy',
      description = 'CoAPy implements the Constrained Application Protocol in Pythong.',
      author='Peter A. Bigot',
      author_email='pab@peoplepowerco.com',
      url='http://coapy.sourceforge.net',
      # Also change in README.TXT, pyxb/__init__.py, and doc/conf.py
      version=version,
      license='BSD License',
      long_description='',
      provides=[ 'CoAPy' ],
      packages=packages,
      package_data=package_data,
      cmdclass = { 'test' : test,
                   'update_version' : update_version },
      classifiers = [ 'Development Status :: 2 - Pre-Alpha'
                      , 'Intended Audience :: Developers'
                      , 'License :: OSI Approved :: BSD License'
                      ] )

