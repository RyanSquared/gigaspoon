#!/bin/bash
# vim:set noet sts=0 sw=2 ts=2:

export PATH="$(pyenv root)/shims:$PATH"

check() {
	if ! which $1 >&-; then
		echo "Install $1"
		exit 1
	fi
}

check yq || exit 1
check pyenv || exit 1

for python in $(yq -rM '.python | .[]' .travis.yml); do
	# Set up Python
	echo "====="
	echo "Setting up Python version ${python}"
	echo "====="
	pyenv install $python -s >/dev/null || pyenv install ${python}-dev -s
	pyenv global $python >/dev/null
	pip install --user virtualenv >/dev/null

	# Loop through environment variables
	for variable in $(yq -rM '.env | .[]' .travis.yml); do

		# Set up environment
		eval "export $variable"

		# Set up virtualenv
		mkdir -p build/venv$python
		python -m virtualenv build/venv$python >/dev/null
		source build/venv$python/bin/activate

		# Install dependencies
		yq -rM '.install | .[]' .travis.yml | while read install_command; do
			eval $install_command
		done

		# Run tests
		echo "Running tests: Python${python} with ${variable}"
		yq -rM '.script | .[]' .travis.yml | while read script_command; do
			eval $script_command
		done

		# Deactivate virtualenv and clean up
		deactivate
		rm -rf build/venv$python

	done

done
