from __future__ import print_function
import re
import os
import sys

import toml



class Dependency_Checker:

	def __init__(self, dir):
		self.compiled_dependencies_list = []
		self.cargo_dependencies = []
		self.extern_crate_declerations = []
		self.plugins = []
		self.dir = dir
		

	def run(self):
		self.error = False
		self.walk_files(self.dir) 
		self.parse_tomls(self.dir)
		return self.check_deps()

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
		"walk files will check all rust files including lib.rs for 'extern crate' and 'use' statements"
		count = 0
		for files in os.walk(folder):
			# Check subfolders but not in top directory
			if (count):
				for i in files[1]:
					# resursivley go into subdirectories
					self.walk_files(files[0] + os.sep + i)
			for item in files[2]:
				if os.path.splitext(item)[1] == ".rs":
					self.parse_file(files[0] + os.sep + item)
			count = count + 1

	def parse_dependencies(self, contents):
		# Compile a regex looking for dependencies being used
		# This only cares about the top level, so for example azure::azure_hl will just return 'azure'
		use_stmt = re.compile('use (\w*)(?:::|;)')
		# 'extern crate *' This will return a list of tuples, the second item will be the alias
		extern_stm = re.compile('extern\scrate\s?([a-zA-Z0-9\-\_]*)(?:\sas\s([a-zA-Z0-9\-\_]*))?')
		plugin_decl = re.compile('\#\!\[plugin\(([a-zA-Z0-9\-\_]*)')

		found_use = use_stmt.findall(contents)
		found_extrn = extern_stm.findall(contents)
		found_plugin = plugin_decl.findall(contents)
		if (found_use):
			# By calling set we can remove duplicates and keep distinct values
			self.compiled_dependencies_list = list(set(found_use + self.compiled_dependencies_list))

		# extern crates are a bit more complicated because they could have aliases, so we need to reduce most of them down to a string
		# but leave the alias ones as a tuple
		if (found_extrn):
			found_extrn = map(self.filter_externs, found_extrn)
			self.extern_crate_declerations = list(set(found_extrn + self.extern_crate_declerations))

		if (found_plugin):
			self.plugins = list(set(found_plugin + self.plugins))

	def filter_externs(self, extern):
		"Reduce an array of tuples down to strings, only leaving tuples for the aliases"
		"Cargo dependencies with a hyphenget converted to underscores, so take account for that"
		if extern[1]:
			extern = (extern[0].replace('-', '_'), extern[1])
			return extern
		else:
			return ''.join(extern).replace('-', '_')



	def parse_tomls(self, folder):
		folder = os.walk(folder)
		for files in folder:
			for i in files[2]:
				if os.path.splitext(i)[1] == '.toml':
					with open(files[0] + os.sep + i) as conffile:
						try:
							config = toml.loads(conffile.read())
							# Add built-in packages to the list so we don't get warnings for example 'plugins listed but not used'
							self.compiled_dependencies_list = list(set([config['package']['name']] + self.compiled_dependencies_list))
							for dep in config['dependencies']:
								# if not dep_in_toml(dep):
								# Need to keep track of the Cargo file the dependency was requested from
								# We also can't check dependencies until all Cargos have been scanned, so store them for now
								self.cargo_dependencies.append((dep.replace('-', '_'), os.path.abspath(conffile.name)))
						except ValueError as e:
							print("ERROR: Failed to parse " + os.path.abspath(conffile.name), file=sys.stderr)
							print (e, file=sys.stderr)
							sys.exit(1)


	def check_cargo_against_extern_crates(self, cargo_dep):
		extern_crate_declerations_and_plugins = self.extern_crate_declerations + self.plugins
		for extern in extern_crate_declerations_and_plugins:
			extern_value = extern if type(extern) is not tuple else extern[0]
			if cargo_dep == extern_value:
				return True

		return False


	def check_deps(self):
		print('Checking Cargo files..\n')
		for cargo_dep in self.cargo_dependencies:
			if not self.check_cargo_against_extern_crates(cargo_dep[0]):
				print('no match with '+ cargo_dep[0] + ' in ' + cargo_dep[1])
				self.error = True

		print('\nChecking extern_crates against use statement\n')
		for extern in self.extern_crate_declerations:
			extern = extern if type(extern) is not tuple else extern[1]
			if (extern) not in self.compiled_dependencies_list:
				print('Error ' + extern + ' not being used!') 
			# if (cargo_dep[0] not in self.compiled_dependencies_list):
			# 	# print("Error: " + cargo_dep[0] + " listed as dependency but not used. Found in " + cargo_dep[1])
			# 	self.error = True
		if self.error:
			return False
		return True


if __name__ == '__main__':
	# First gather all the modules being used so we don't have to parse them again
	components = '..' + os.sep + 'components'
	dc = Dependency_Checker(components)
	if dc.run():
		sys.exit(0)
	sys.exit(1)
