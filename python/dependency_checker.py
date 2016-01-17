from __future__ import print_function
import re
import os
import sys

import toml


class Dependency_Checker:

	def __init__(self, dir):
		self.compiled_dependencies_list = []
		self.cargo_dependencies = []
		self.walk_files(dir)
		self.parse_tomls(dir)
		self.check_deps()

	def dep_in_toml(self, dependency):
		for i in self.cargo_dependencies:
			for dep in i[0]:
				if dep == dependency:
					return True
		return False

	def parse_file(self, filename):
		with open(filename, 'r') as f:
			data = f.read()
			self.parse_dependencies(data)

	def walk_files(self, folder):
		folder = os.walk(folder)
		count = 0
		for files in folder:
			# Check subfolders but not in top directory
			if (count):
				for i in files[1]:
					# resursivley go into subdirectories
					self.walk_files(files[0] + os.sep + i)
			for item in files[2]:
				if os.path.splitext(item)[1] is ".rs":
					self.parse_file(files[0] + os.sep + item)
			count = count + 1

	def parse_dependencies(self, contents):
		# Compile a regex looking for dependencies being used
		# This only cares about the top level, so for example azure::azure_hl will just return 'azure'
		pattern = re.compile('use (\w*)(?:::|;)')
		m = pattern.findall(contents)
		# By calling set we can remove duplicates and keep distinct values
		self.compiled_dependencies_list = list(set(m + self.compiled_dependencies_list))

	def parse_tomls(self, folder):
		folder = os.walk(folder)
		for files in folder:
			for i in files[2]:
				if os.path.splitext(i)[1] == '.toml':
					with open(files[0] + os.sep + i) as conffile:
						try:
							config = toml.loads(conffile.read())
							for dep in config['dependencies']:
								# if not dep_in_toml(dep):
								# Need to keep track of the Cargo file the dependency was requested from
								# We also can't check dependencies until all Cargos have been scanned, so store them for now
								self.cargo_dependencies.append((dep, os.path.abspath(conffile.name)))
						except ValueError as e:
							print("ERROR: Failed to parse " + os.path.abspath(conffile.name), file=sys.stderr)
							print (e, file=sys.stderr)
							sys.exit(1)


	def check_deps(self):
		for cargo_dep in self.cargo_dependencies:
			if (cargo_dep[0] not in self.compiled_dependencies_list):
				print("Error " + cargo_dep[0] + " listed as dependency but not used. Found in " + cargo_dep[1], file=sys.stderr)
				sys.exit(1)
			return True


if __name__ == '__main__':
	# First gather all the modules being used so we don't have to parse them again
	components = '..' + os.sep + 'components'
	Dependency_Checker(components)