# Contributing to RT-RAMSIS Development

# General Guidelines

- We try to stick to established community standards wherever possible. If your
  unsure of how something should be done, sticking to how others have done it
  is generally a good idea. 
- We use the [git-flow](https://nvie.com/posts/a-successful-git-branching-model/) 
  branching model, i.e. the **master** branch contains 
  major milestones only (releases) that have been tested to some extent
- The main development branch is **develop**
- Generally don't push to the **develop** branch directly. Instead, create a
  feature branch, push it, and create a merge request which can be reviewed by
  the other devs.
- Make granular commits of things that are related, don't put everything into
  one huge commit. This makes it a lot easier to review incoming changes.
- Write proper commit messages that explain what changes with the commit and
  why. Use imperative present tense like [many others](https://stackoverflow.com/questions/3580013/should-i-use-past-or-present-tense-in-git-commit-messages) do.

## Environment

- We target python 3.6 and PyQt 5.12 LTS. Set up a *virtualenv* to keep things 
  separate:
  
  ```bash
  virtualenv --python=/usr/bin/python3.6 <path/to/myvirtualenv>
  . <path/to/myvirtualenv>/bin/activate
  pip install -r requirements.txt
  ```
  
- Anything from the standard library may be used at your own discretion. Think
  twice about adding 3rd party dependencies and make sure they are reasonably
  well established and maintained.
- Use your favorite editor to write your code but don't assume others will have
  the same preferences. So avoid adding IDE specific stuff to the repo or your 
  code. You may amend `.gitignore` anytime.
- The "official" repository resides on `gitlab.seismo.ethz.ch`
- The code is currently unreleased and as such, unlicensed. It belongs to ETH
  and you do not have permission to distribute it. However, we will most likely
  target the [AGPL v3](https://www.gnu.org/licenses/agpl.html) for whenever we 
  will have to [convey](https://www.gnu.org/licenses/gpl-faq.html#WhyPropagateAndConvey) 
  the code to someone else, so make sure everything you add is AGPL compatible.

## Testing

- Write unit tests for your code where possible. We'll run them with 
  **gitlab-ci** whenever you push new commits.

## Coding Styleguide

- Stick to [PEP8](https://www.python.org/dev/peps/pep-0008) and 
  [PEP257](http://www.python.org/dev/peps/pep-0257) (details and exceptions
  below). Your code will be checked with flake8 when you push it to the 
  repository.
- Look at the existing code and try to make yours look similar.
- Document your code properly (see below)
- Add additional comments where they help to understand what's going on.
   
**Clarifications & Style Details**

- String formatting. We used f-strings everywhere since they use less space 
  whereas traditional .format() strings are often over-length and need to be 
  split across multiple lines.
- Use absolute imports. This will make it easier for Sphinx and other external
  tools to find everything.
  

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
- Add file headers as follows:

    ```python
    # Copyright 2018, ETH Zurich - Swiss Seismological Service SED
    """
    Short module description (one line)
  
    Extended description (multiple lines)
    Followed by a blank line
  
    """
    
    ```
    Rationale: The docstring will be picked up by Sphinx and is used to 
    document what the module is about. The copyright is ETH in accordance with 
    Swiss
    [copyright law](https://www.admin.ch/opc/en/classified-compilation/19920251/index.html#a17).
    However, this should not go into the docs for each module, so it's a 
    separate comment. The blank line before the closing quotes is for symmetry 
    and because BDFL recommends it to help with auto-formatting in vim/emacs.
    Don't add author, version, etc. information. It's redundant, the VCS does a 
    much better job of keeping track of this.
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