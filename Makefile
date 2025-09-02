builddist:
	python setup.py check
	python setup.py sdist
	python setup.py bdist_wheel --universal

install:
	pip install .

twine:
	twine upload dist/monarchmoney_enhanced*

uninstall:
	pip uninstall monarchmoney-enhanced

clean:
	rm -fR build dist monarchmoney_enhanced.egg-info monarchmoney/__pycache__ *.json