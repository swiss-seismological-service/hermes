# Contributing to RT-RAMSIS Development

# General Guidelines

- The master branch contains major milestones only (releases) that have been
  tested to some extent
- The main development branch is **develop**
- Generally don't push to the **develop** branch directly. Instead, create a
  feature branch, push it, and create a merge request which can be reviewed by
  the other devs.
- Make granular commits of things that are related, don't put everything into
  one huge commit. This makes it a lot easier to review incoming changes.
- Write proper commit messages that explain what changes with the commit and
  why.


## Styleguide

- Please stick to [PEP8](https://www.python.org/dev/peps/pep-0008)
- Look at the existing code and try to make yours look similar
- Document your code properly (see below)
- Add additional comments where they help to understand what's going on.

# Documentation

**RT-RAMSIS Code Documentation**

RT-RAMSIS documentation is generated with
[Sphinx](http://sphinx-doc.org/contents.html). You can build and access the
code documentation for RT-RAMSIS as follows

1. Make sure you're in a working RAMSIS development environment, i.e. that all
   module includes are available.
2. ``cd`` to the ``doc`` directory
3. Run ``make html``.
4. Open ``doc/_build/html/index.html``
    
Please follow the following guidelines for documenting your code:

- Be consistent with existing code documentation
- Don't use fancy file headers and ascii comment decorations like [this]
  (https://hackerboss.com/get-rid-of-templates/). Also don't include version or 
  author or other redundant information which someone will forget to update
  eventually (i.e. anything that can be found in the version control system, 
  license file, etc.). Again, be consistent with existing code.
- Add `:`-style
  [docstrings](https://www.jetbrains.com/pycharm/help/using-docstrings-to-specify-types.html)
  to methods for type hinting and to describe what each method does.
- Link to module, method or class documentations where appropriate (see [Sphinx
  Cross Referencing
  Syntax](http://sphinx-doc.org/domains.html#cross-referencing-syntax). Since
  Sphinx' default_role is set to 'any', many references will work when enclosed
  in simple backticks (e.g. \`\`module\`\`)
- Enclose method, attribute, module and class names etc in double back ticks
  \`\`
- Don't document the `__init__` method. Document the parameters for init in the
  class' docstring instead.


**PyQt**

- PyQt5 reference guide: http://pyqt.sourceforge.net/Docs/PyQt5/

**PyQGis**

- The QGis API Documentation for C++: http://qgis.org/api/
- The PyQGis developer cookbook (recipes):
  http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/
- A book on PyQGis programming http://locatepress.com/ppg
