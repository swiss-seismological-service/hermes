# Makefile for epydoc documentation
#

EPYDOC    = epydoc
RAMSISDIR = ../ramsis

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html to make standalone HTML files"

html:
	$(EPYDOC) --html -o html $(RAMSISDIR)
	@echo
	@echo "Build finished. The HTML pages are in html."
