# -----------------------------------------------------------------------------
# This is <Makefile>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2018/01/26        V0.1    Daniel Armbruster (SED, ETHZ)
#
# =============================================================================
#
# To install RAMSIS invoke:
# 	
# 	$ make install [VENV=PATH_TO_VENV]
#
# To use a Python interpreter instance from a virtual environment pass the VENV
# variable. The default is your python3 interpreter in your PATH.
#
# =============================================================================

PYTHON=$(shell which python3)
PYTHON_PIP=$(shell which pip3)
PYRCC=$(shell which pyrcc5)

ifneq ($(VENV),)
PYTHON=$(realpath $(VENV)/bin/python3)
PYTHON_PIP=$(realpath $(VENV)/bin/pip3)
PYRCC=$(realpath $(VENV)/bin/pyrcc5)
endif

PATH_RAMSIS_SRC=RAMSIS
REQUIREMENTS=requirements-py36-linux64.txt

# -----------------------------------------------------------------------------
#
CHECK_DEP=$(strip $(shell which $(1))) 
CHECK_VENV_DEP=$(strip \
							 $(shell . $(VENV)/bin/activate && which $(1) && deactivate)) 
OQ_CHECK:=$(call CHECK_DEP,oq)
PYQT5_CHECK:=$(call CHECK_DEP,pyrcc5)
ifneq ($(VENV),)
OQ_CHECK:=$(call CHECK_VENV_DEP,oq)
PYQT5_CHECK:=$(call CHECK_VENV_DEP,pyrcc5)
endif

# -----------------------------------------------------------------------------
.PHONY: install
install: $(PATH_RAMSIS_SRC)/ui/views/images_rc.py install_requirements
	$(PYTHON_PIP) install -e .

.PHONY: install_requirements
install_requirements: $(REQUIREMENTS)
	$(if $(OQ_CHECK),,$(error ERROR: OpenQuake not installed))
	$(PYTHON_PIP)	install -U -r $<

$(PATH_RAMSIS_SRC)/ui/views/images_rc.py: \
	$(PATH_RAMSIS_SRC)/ui/views/images.qrc
	$(if $(PYQT5_CHECK),,$(error ERROR: PyQt5 not installed))
	$(PYRCC) -o $(PATH_RAMSIS_SRC)/ui/views/images_rc.py $(word 1,$^)

# ---- END OF <Makefile> ----
