# Makefile for epydoc documentation
#

EPYDOC    = epydoc
RAMSISDIR = ../../ramsis
BUILDDIR  = _build

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html to make standalone HTML files"

html:
	# Temporarily convert to Python package during build
	touch $(RAMSISDIR)/__init__.py
	$(EPYDOC) --html -o html $(RAMSISDIR)
	-rm -f $(RAMSISDIR)/__init__.py $(RAMSISDIR)/__init__.pyc
	mkdir $(BUILDDIR)
	mv html $(BUILDDIR)
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."
