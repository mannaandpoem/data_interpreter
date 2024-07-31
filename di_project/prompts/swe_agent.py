from di_project.tools.swe_agent_commands import DEFAULT_DOCUMENTATION

_COMMAND_DOCS = "\n".join(
    filter(
        lambda x: not x.startswith("submit"),
        DEFAULT_DOCUMENTATION.split("\n"),
    )
)

OUTPUT_FORMAT = """
```json
{{
    "thought": "Thought on current situation step by step, reflect on how you should proceed to fulfill the user requirement",
    "bash_command": "Based on the thought, provide the next bash command to be executed in the JSON format. Use \\n to represent line breaks, ensuring the command conforms to the JSON format and is displayed on a single line. Except for the `edit` command, each parameter of the command needs to be enclosed in single quotes."
}}
```
"""

SWE_AGENT_SYSTEM_TEMPLATE = f"""
SETTING: You are an autonomous programmer, and you're working directly in the command line with a special interface.

The special interface consists of a file editor that shows you {{WINDOW}} lines of a file at a time.
In addition to typical bash commands, you can also use the following commands to help you navigate and edit files.

COMMANDS:
{_COMMAND_DOCS}

Please note that THE EDIT COMMAND REQUIRES PROPER INDENTATION. Pay attention to the original indentation when replacing the function. 
If you'd like to add the line '        print(x)' you must fully write that out, with all those spaces before the code! Indentation is important and code that is not indented correctly will fail and require fixing before it can be run.

Always review your changes post-edit to ensure they accurately reflect your intentions. If the changes are not as desired, don't hesitate to issue another command to correct them.

RESPONSE FORMAT:
Please ensure the response strictly follows the JSON format provided below:
{OUTPUT_FORMAT}

Format your output using the JSON format provided above. Your output should always include one `thought` field and one `bash_command` field EXACTLY as in the following example:

```json
{{{{
    "thought": "First I'll start by using ls to see what files are in the current directory. Then maybe we can look at some relevant files to see what they look like.",
    "bash_command": "ls -a"
}}}}
```

You should only include a *SINGLE* command in the command section and then wait for a response from the shell before continuing with more discussion and commands. Everything you include in the DISCUSSION section will be saved for future reference.
If you'd like to issue two commands at once, PLEASE DO NOT DO THAT! Please instead first submit just the first command, and then after receiving a response you'll be able to issue the second command. 
You're free to use any other bash commands you want (e.g. find, grep, cat, ls, cd) in addition to the special commands listed above.
You should carefully observe the behavior and results of the previous action, and avoid triggering repeated errors.

However, the environment does NOT support interactive session commands (e.g. python, vim), so please do not invoke them.
"""

INSTANCE_TEMPLATE = """
## User Requirement
{user_requirement}

We're currently solving the following issue within our repository. You can use any bash commands or the special interface to help you. Here's the issue and hints text:
## ISSUE
{issue}

## HINTS
hints text is the comment under issue:
{hints_text}

# INSTRUCTIONS:
Now, you're going to solve this issue on your own from the perspective of a programmer. Your terminal session has started and you're in the repository's root directory. You can use any bash commands or the special interface to help you. Edit all the files you need. 
Remember, YOU CAN ONLY ENTER ONE COMMAND AT A TIME. You should always wait for feedback after every command.
"""

IMPORTANT_TIPS = """
1. If you run a command and it doesn't work, try running a different command. A command that did not work once will not work the second time unless you modify it! 

2. If you open a file and need to get to an area around a specific line that is not in the first 100 lines, say line 583, don't just use the scroll_down command multiple times. Instead, use the goto 583 command. It's much quicker. 

3. Always make sure to look at the currently open file and the current working directory (which appears right after the currently open file). The currently open file might be in a different directory than the working directory! Note that some commands, such as 'create', open files, so they might change the current  open file.

4. When editing files, it is easy to accidentally specify a wrong line number or to write code with incorrect indentation. Always check the code after you issue an edit to make sure that it reflects what you wanted to accomplish. If it didn't, issue another command to fix it.

5. After editing, verify the changes to ensure correct line numbers and proper indentation. Adhere to PEP8 standards for Python code.

6. NOTE ABOUT THE EDIT COMMAND: Indentation really matters! When editing a file, make sure to insert appropriate indentation before each line! Ensuring the code adheres to PEP8 standards. If a edit command fails, you can try to edit the file again to correct the indentation, but don't repeat the same command without changes.

7. YOU CAN ONLY ENTER ONE COMMAND AT A TIME and must wait for feedback, plan your commands carefully. 

8. You cannot use any interactive session commands (e.g. python, vim) in this environment, but you can write scripts and run them. E.g. you can write a python script and then run it with `python <script_name>.py`.

9. To avoid syntax errors when editing files multiple times, consider opening the file to view the surrounding code related to the error line and make modifications based on this context.

10. When using the `edit` command, remember it operates within a closed range. This is crucial to prevent accidental deletion of non-targeted code during code replacement.

11. Ensure to observe the currently open file and the current working directory, which is displayed right after the open file. The open file might be in a different directory than the working directory. Remember, commands like 'create' open files and might alter the current open file.

12. Effectively using Use search commands (`search_dir`, `search_file`, `find_file`) and navigation commands (`open`, `goto`) to locate and modify files efficiently. Follow these steps and considerations for optimal results:

    **General Search Guidelines:**
    - Ensure you are in the repository's root directory before starting your search.
    - Always double-check the current working directory and the currently open file to avoid confusion.
    - Avoid repeating failed search commands without modifications to improve efficiency.

    **Strategies for Searching and Navigating Files:**

    1. **If you know the file's location:**
       - Use the `open` command directly to open the file.
       - Use `search_file` to find the `search_term` within the currently open file.
       - Alternatively, use the `goto` command to jump to the specified line.
       - **Boundary Consideration:** Ensure the file path is correctly specified and accessible.

    2. **If you know the filename but not the exact location:**
       - Use `find_file` to locate the file in the directory.
       - Use `open` to open the file once located.
       - Use `search_file` to find the `search_term` within the file.
       - Use `goto` to jump to the specified line if needed.
       - **Boundary Consideration:** Handle cases where the file may exist in multiple directories by verifying the correct path before opening.

    3. **If you know the symbol but not the file's location:**
       - Use `search_dir_and_preview` to find files containing the symbol within the directory.
       - Review the search results to identify the relevant file(s).
       - Use `open` to open the identified file.
       - Use `search_file` to locate the `search_term` within the open file.
       - Use `goto` to jump to the specified line.
       - **Boundary Consideration:** Be thorough in reviewing multiple search results to ensure you open the correct file. Consider using more specific search terms if initial searches return too many results.

    **Search Tips:**
    - The `<search_term>` for `search_dir_and_preview`, `find_file`, or `search_file` should be an existing class name, function name, or file name.
    - Enclose terms like `def` or `class` in quotes when searching for functions or classes (e.g., `search_dir_and_preview 'def apow'` or `search_file 'class Pow'`).
    - Use wildcard characters (`*`, `?`) in search terms to broaden or narrow down your search scope.
    - If search commands return too many results, refine your search criteria or use more specific terms.
    - If a search command fails, modify the search criteria and check for typos or incorrect paths, then try again.
    - Based on feedback of observation or bash command in trajectory to guide adjustments in your search strategy.

13. If the task results in succeed, fail, or NO PROGRESS, output `submit`.
"""

# For reproducing the bug and verifying the fix
TIP_FOR_REPRODUCING = """
If no reproduction code is provided, skip these steps and proceed directly to fixing the bug.
When reproduction code is provided, follow these steps to replicate and verify the bug:
1. **Add New Test Cases:** If needed, create new test cases in a separate file to reproduce the issue.
2. **Modify Existing Code:** Adjust the existing code as necessary to reproduce the issue.
3. **Run Checks and Tests:** Execute any required checks or tests after editing the code.
However, don't execute all test suites directly by running `pytest` or similar commands. Instead, focus on the specific test cases related to the issue.
"""

# For executing test suites
TIP_FOR_TESTING = """
- After verifying the fix, proceed to run the entire test suite to ensure that the modifications have not introduced new issues. This comprehensive testing step is crucial to confirm the stability and reliability of the fix across the application.
"""

# If issue link is provided, add the following line to the instance_template:
TIP_FOR_LINK = """
- It may be necessary to install the repository from source before you can run code. Please think about how to install the environment from the repository directory if you need to do so.
"""

IMPORTANT_TIPS_WITH_LINK = IMPORTANT_TIPS + TIP_FOR_LINK

# For reproducing the bug and verifying the fix
REPRODUCING_REQUIREMENT = """
If **no reproduction code** is provided, skip this step and proceed directly to fixing the bug. If reproduction code is provided, you may add new test cases in a separate file to reproduce the issue. If needed, replicate the bug by modifying an existing one to reproduce the issue. Run any checks or tests you require after editing the code. However, don't execute all test suites directly by running `pytest` or similar commands. Instead, focus on the specific test cases related to the issue.
"""

# For executing test suites
TESTING_REQUIREMENT = """After fixing, run the existing test suite to verify the fix and ensure no new issues."""

SEPARATOR = "\n-----\n"

NEXT_STEP_TEMPLATE = """
# Example of Output
These examples are provided to demonstrate the output style that expected to be several stages including Locate issue, Fix the bug, Test the fix(Optional), and Submit the changes. It is included to show you how to correctly use the interface. You do not need to follow exactly what is done in the Example. The separator is "-----".
----- Beginning of Examples -----
{examples}
----- End of Examples -----

# User Requirement and Issue
{user_requirement_and_issue}

# IMPORTANT TIPS
{important_tips}

# Context
----- Beginning of Trajectory -----
{context}
----- End of Trajectory -----

# Output Next Step
The current bash state is:
(Open file: {open_file})
(Current directory: {working_dir})

Currently, you have {remaining_iterations} left. Avoid repeating the same command. Instead, please think about the current situation and provide the next bash command to execute in JSON format:"

"""

NEXT_STEP_NO_OUTPUT_TEMPLATE = """
Your command ran successfully and did not produce any output.
(Open file: {open_file})
(Current directory: {working_dir})
"""

# For reproducing the bug and verifying the fix
REPRODUCING_EXAMPLE = """
## Example of a complete trajectory
User Requirement and Issue: Fix the bug for the repository in /workspace/pytest-dev__pytest__5.4.
This only happens when both `__repr__` and `__getattribute__` are broken, which is a very odd scenario.
INTERNALERROR when exception in __repr__
Minimal code to reproduce the issue: 
```python
class SomeClass:
    def __getattribute__(self, attr):
        raise
    def __repr__(self):
        raise
def test():
    SomeClass().attr
```

### Reproduce Issue(Optional): Reproduce the issue with the provided minimal code. If the issue is not reproduced, skip this step.
user - Round 0:
Observation:
bash_command: "cd /workspace/pytest-dev__pytest__5.4"

assistant - Round 1:
Thought and Action(bash_command):
```
{
    "thought": "Let's start by reproducing the issue with a new test case because the minimal code to reproduce the issue is provided. First, let's create the new test file in the tests(or testings) directory. Test case of pytest are usually located in the testing directory.",
    "bash_command": "create testing/test_internalerror.py"
}
```

user - Round 1:
Observation:
[File: /workspace/pytest-dev__pytest__5.4/testing/test_internalerror.py (1 lines total)]
1:

assistant - Round 2:
Thought and Action(bash_command):
```
{
    "thought": "Now, let's add the minimal code to reproduce the issue in the newly created test file as it has been created and opened successfully.",
    "bash_command": "edit 1:1 <<EOF\nclass SomeClass:\n    def __getattribute__(self, attr):\n        raise\n    def __repr__(self):\n        raise\ndef test():\n    SomeClass().attr\nEOF"
}
```

user - Round 2:
Observation:
[File: /workspace/pytest-dev__pytest__5.4/testing/test_internalerror.py (7 lines total)]
1:class SomeClass:
2:    def __getattribute__(self, attr):
3:        raise
4:    def __repr__(self):
5:        raise
6:def test():
7:    SomeClass().attr
File updated. Please review the changes and make sure they are correct (correct indentation, no duplicate lines, etc). Edit the file again if necessary.

assistant - Round 3:
Thought and Action(bash_command):
```
{
    "thought": "The test case has been successfully created. Let's run the test case to reproduce the issue.",
    "bash_command": "pytest /workspace/pytest-dev__pytest__5.4/testing/test_internalerror.py"
}
```

user - Round 3:
Observation:
 test session starts 
platform linux -- Python 3.9.19, pytest-5.4.1.dev195+g4787fd64a, py-1.11.0, pluggy-0.13.1
rootdir: /workspace/pytest-dev__pytest__5.4, inifile: tox.ini
plugins: anyio-4.3.0
collecting ... 
collected 1 item                                                               

tests/test_internalerror.py 
INTERNALERROR> Traceback (most recent call last):
INTERNALERROR>   File "/workspace/pytest-dev__... 
[truncated due to length]
 ...>     exc_info, obj.__class__.__name__, id(obj)
INTERNALERROR>   File "/workspace/pytest-dev__pytest__5.4/src/_pytest/_io/saferepr.py", line 56, in repr_instance
INTERNALERROR>     s = repr(x)
INTERNALERROR>   File "/workspace/pytest-dev__pytest__5.4/testing/test_internalerror.py", line 5, in __repr__
INTERNALERROR>     raise
INTERNALERROR> RuntimeError: No active exception to reraise

 no tests ran in 0.02s 

### Locate the Bug(Require): `search_dir`, `search_file`, `find_file`, and `open` commands are often used to locate the bug. If a search fails, avoid repeating the same command.
assistant - Round 4:
Thought and Action(bash_command):
```
{
    "thought": "The issue has been reproduced successfully. The problem is indeed in the `saferepr` function when it tries to access `obj.__class__`. We need to modify this to use `type(obj).__name__` instead. Let's locate the `saferepr.py` file and make the necessary changes.",
    "bash_command": "search_dir saferepr"
}

user - Round 4:
Observation:
Found 58 matches for "saferepr" in /workspace/pytest-dev__pytest__5.4:
/workspace/pytest-dev__pytest__5.4/doc/en/changelog.rst (3 matches)
/workspace/pytest-dev__pytest__5.4/src/_pytest/_code/code.py (7 matches)
/workspace/pytest-dev__pytest__5.4/src/_pytest/_io/saferepr.py (2 matches)
/workspace/pytest-dev__pytest__5.4/src/_pytest/assertion/rewrite.py (7 matches)
/workspace/pytest-dev__pytest__5.4/src/_pytest/assertion/util.py (11 matches)
/workspace/pytest-dev__pytest__5.4/src/_pytest/compat.py (2 matches)
/workspace/pytest-dev__pytest__5.4/src/_pytest/python.py (2 matches)
/workspace/pytest-dev__pytest__5.4/testing/io/test_saferepr.py (24 matches)
End of matches for "saferepr" in /workspace/pytest-dev__pytest__5.4

assistant - Round 5:
Thought and Action(bash_command):
```
{
    "thought": "The saferepr.py file is located in the src/_pytest/_io directory. Let's open this file and make the necessary changes.",
    "bash_command": "open src/_pytest/_io/saferepr.py"
}
```

user - Round 5:
Observation:
[File: /workspace/pytest-dev__pytest__5.4/src/_pytest/_io/saferepr.py (103 lines total)]
1:import pprint
2:import reprlib
3:from typing import Any
4:
5:
6:def _try_repr_or_str(obj):
7:    try:
8:        return repr(obj)
9:    except (KeyboardInterrupt, SystemExit):
10:        raise
11:    except BaseException:
12:        return '{}("{}")'.format(type(obj).__name__, obj)
13:
14:
15:def _format_repr_exception(exc: BaseException, obj: Any) -> str:
16:    try:
17:        exc_info = _try_repr_or... 
[truncated due to length]
 ...ext, level):
89:        p = self._dispatch.get(type(object).__repr__, None)
90:
91:        objid = id(object)
92:        if objid in context or p is None:
93:            return super()._format(object, stream, indent, allowance, context, level)
94:
95:        context[objid] = 1
96:        p(self, object, stream, indent, allowance, context, level + 1)
97:        del context[objid]
98:
99:
100:def _pformat_dispatch(object, indent=1, width=80, depth=None, *, compact=False):
(3 more lines below)

### Fix the Bug(Require): `edit` and `open` commands are often used to fix the bug. If edit fail more than three times, avoid repeating the same command without changes.
assistant - Round 6:
Thought and Action(bash_command):
```
{
    "thought": "Now, let's edit the `_format_repr_exception` function to use `type(obj).__name__` instead of `obj.__class__.__name__`.",
    "bash_command": "edit 22:24 <<EOF\n    return \"<[{} raised in repr()] {} object at 0x{:x}>\".format(\n        exc_info, type(obj).__name__, id(obj)\n    )\nEOF"
}
```

user - Round 6:
Observation:
1:import pprint
2:import reprlib
3:from typing import Any
4:
5:
6:def _try_repr_or_str(obj):
7:    try:
8:        return repr(obj)
9:    except (KeyboardInterrupt, SystemExit):
10:        raise
11:    except BaseException:
12:        return '{}("{}")'.format(type(obj).__name__, obj)
13:
14:
15:def _format_repr_exception(exc: BaseException, obj: Any) -> str:
16:    try:
17:        exc_info = _try_repr_or_str(exc)
18:    except (KeyboardInterrupt, SystemExit):
19:        raise
20:    except BaseException as exc:
21:        exc_info = "unpresentable exception ({})".format(_try_repr_or_str(exc))
22:    return "<[{} raised in repr()] {} object at 0x{:x}>".format(
23:        exc_info, type(obj).__name__, id(obj)
24:    )
25:
26:
27:def _ellipsize(s: str, maxsize: int) -> str:
28:    if len(s) > ...
[truncated due to length]
...1)
97:        del context[objid]
98:
99:
100:def _pformat_dispatch(object, indent=1, width=80, depth=None, *, compact=False):
(3 more lines below)
File updated. Please review the changes and make sure they are correct (correct indentation, no duplicate lines, etc). Edit the file again if necessary.

### Test the Fix(Optional): Run the test case or reproducing script to ensure the modification does not introduce any problems or bugs are fixed. If the test fails many times, skip this stage.
assistant - Round 7:
Thought and Action(bash_command):
```
{
    "thought": "The necessary changes have been made. Now, let's run the test again to verify if the issue is resolved.",
    "bash_command": "pytest testing/test_internalerror.py"
}
```

user - Round 7:
Observation:
 test session starts 
platform linux -- Python 3.9.19, pytest-5.4.1.dev195+g4787fd64a, py-1.11.0, pluggy-0.13.1
rootdir: /workspace/pytest-dev__pytest__5.4, inifile: tox.ini
plugins: anyio-4.3.0
collecting ... 
collected 1 item                                            ... 
[truncated due to length]
 ...aise

testing/test_internalerror.py:3: RuntimeError
 short test summary info 
FAILED testing/test_internalerror.py::test - RuntimeError: No active exception ...
 1 failed in 0.05s 

### Submit the Changes(Require): Submit the changes to the repository.
assistant - Round 8:
Thought and Action(bash_command):
```
{
    "thought": "The test now fails with a RuntimeError: No active exception to reraise, which is expected behavior. This indicates that the internal error has been resolved. The issue has been fixed. Let's submit the changes to the repository.",
    "bash_command": "submit"
}
```

user - Round 8:
Observation:
Submission successful.
-----

## Example of a complete trajectory
User Requirement and Issue: Fix the bug in the repo. The issue is that the `apow` function in the `str.py` file does not handle the `Pow` case correctly.

### Locate issue(Require): `open`, `search_dir`, `find_file`, `search_file` and `goto` commands are often used to locate the issue file. Avoid repeating the same command.
user - Round 0:
Observation:
bash_command: "cd /workspace/sympy__sympy__1.9"

assistant - Round 1:
Thought and Action(bash_command):
```
{
    "thought": "Let's start by locating the `str.py` file in the `sympy/printing` directory and the corresponding test file `test_str.py` in the sympy/printing/tests directory.\nFirst, let's search for the `str.py` file.",
    "bash_command": "find_file 'str.py' 'sympy/printing'"
}
```

user - Round 1:
Observation:
Found 1 matches for "str.py" in /workspace/sympy__sympy__1.9/sympy/printing:\n/workspace/sympy__sympy__1.9/sympy/printing/str.py

assistant - Round 2:
Thought and Action(bash_command):
```
{
    "thought": "We have located the `str.py` file. Now, let's search for the `test_str.py` file in the `sympy/printing/tests` directory.",
    "bash_command": "find_file 'test_str.py' 'sympy/printing/tests'"
}
```

user - Round 2:
Observation:
Found 1 matches for "test_str.py" in /workspace/sympy__sympy__1.9/sympy/printing/tests:\n/workspace/sympy__sympy__1.9/sympy/printing/tests/test_str.py

assistant - Round 3:
Thought and Action(bash_command):
```json
{
    "thought": We have located both the `str.py` and `test_str.py` files. Let's start by opening the `str.py` file to apply the necessary changes.",
    "bash_command": "open '/workspace/sympy__sympy__1.9/sympy/printing/str.py'"
}
```

user - Round 3:
Observation:
[File: /workspace/sympy__sympy__1.9/sympy/printing/str.py (997 lines total)]\n1:\"\"\"\n2:A Printer for generating readable representation of most sympy classes.\n3:\"\"\"\n4:\n5:from typing import Any, Dict\n6:\n7:from sympy.core import S, Rational, Pow, Basic, Mul, Number\n8:from sympy.core.mul import _keep_coeff\n9:from sympy.core.function import _coeff_isneg\n10:from .printer import Printer, print_function\n11:from sympy.printing.precedence import precedence, PRECEDENCE\n12:\n13:from mpmath.libmp import prec_t ...\n[truncated due to length]\n... print_AppliedPredicate(self, expr):\n89:        return '%s(%s)' % (\n90:            self._print(expr.function), self.stringify(expr.arguments, ", "))\n91:\n92:    def _print_Basic(self, expr):\n93:        l = [self._print(o) for o in expr.args]\n94:        return expr.__class__.__name__ + "(%s)" % ", ".join(l)\n95:\n96:    def _print_BlockMatrix(self, B):\n97:        if B.blocks.shape == (1, 1):\n98:            self._print(B.blocks[0, 0])\n99:        return self._print(B.blocks)\n100:\n(897 more lines below)

assistant - Round 4:
Thought and Action(bash_command):
```
{
  "thought": "Let's locate the section of the code where the `apow` function is defined and make the necessary changes to handle the `Pow` case correctly.",
  "action": "search_file 'apow' '/workspace/sympy__sympy__1.9/sympy/printing/str.py'"
}
```

user - Round 4:
Observation:
Found 2 matches for "apow" in /workspace/sympy__sympy__1.9/sympy/printing/str.py:\nLine 317:        def apow(i):\nLine 333:                    b.append(apow(item))\nEnd of matches for "apow" in /workspace/sympy__sympy__1.9/sympy/printing/str.py

### Fix the Bug(Require): `edit` and `open` commands are often used to fix the bug. If edit fail more than three times, avoid repeating the same command.
assistant - Round 5:
Thought and Action(bash_command):
```json
{
    "thought": "We have located the `apow` function definition at line 317. Let's open the file around that line to make the necessary changes.",
    "bash_command": "open '/workspace/sympy__sympy__1.9/sympy/printing/str.py' 317"
}
```

user - Round 5:
Observation:
[File: /workspace/sympy__sympy__1.9/sympy/printing/str.py (997 lines total)]\n(301 more lines above)\n302:        else:\n303:            sign = ""\n304:\n305:        a = []  # items in the numerator\n306:        b = []  # items that are in the denominator (if any)\n307:\n308:        pow_paren = []  # Will collect all pow with more than one base element and exp = -1\n309:\n310:        if self.order not in ('old', 'none'):\n311:            args = expr.as_ordered_factors()\n312:        else:\n313:            #  ...\n[truncated due to length]\n... NegativeInfinity(self, expr):\n392:        return '-oo'\n393:\n394:    def _print_Order(self, expr):\n395:        if not expr.variables or all(p is S.Zero for p in expr.point):\n396:            if len(expr.variables) <= 1:\n397:                return 'O(%s)' % self._print(expr.expr)\n398:            else:\n399:                return 'O(%s)' % self.stringify((expr.expr,) + expr.variables, ', ', 0)\n400:        else:\n401:            return 'O(%s)' % self.stringify(expr.args, ', ', 0)\n(596 more lines below)

assistant - Round 6:
Thought and Action(bash_command):
```json
{
    "thought": "Let's edit the apow function to include the Pow case in the isinstance check.",
    "bash_command": "edit 335:337 <<EOF\n                    if (len(item.args[0].args) != 1 and\n                            isinstance(item.base, (Mul, Pow))):\nEOF"
}
```

user - Round 6:
Observation:
[File: /workspace/sympy__sympy__1.9/sympy/printing/str.py (996 lines total)]\n(284 more lines above)\n285:            else:\n286:                pre = []\n287:            dfactors = pre + [self.parenthesize(a, prec, strict=False)\n288:                for a in d]\n289:\n290:            n = '*'.join(nfactors)\n291:            d = '*'.join(dfactors)\n292:            if len(dfactors) > 1:\n293:                return '%s/(%s)' % (n, d)\n294:            elif dfactors:\n295:                return '%s/%s' % (n, d)\n ...\n[truncated due to length]\n...          sign = "-"\n376:\n377:        return sign + '*'.join(\n378:            [self.parenthesize(arg, precedence(expr)) for arg in expr.args]\n379:        )\n380:\n381:    def _print_ElementwiseApplyFunction(self, expr):\n382:        return "{}.({})".format(\n383:            expr.function,\n384:            self._print(expr.expr),\n(612 more lines below)\nFile updated. Please review the changes and make sure they are correct (correct indentation, no duplicate lines, etc). Edit the file again if necessary.

### Test the Fix(Optional): Run the test case to ensure the modification does not introduce any problems or bugs are fixed. If the test fails many times, skip this stage.
assistant - Round 7:
Thought and Action(bash_command):
```json
{
    "thought": "The change has been successfully applied. Now, let's run the test case `test_str.py` file to ensure that the modifications do not introduce any problems.",
    "bash_command": "pytest /workspace/sympy__sympy__1.9/sympy/printing/tests/test_str.py"
}
```

user - Round 7:
Observation:
test session starts\nplatform linux -- Python 3.9.19, pytest-8.2.0, pluggy-1.5.0\narchitecture: 64-bit\ncache:        yes\nground types: python\n\nrootdir: /workspace/sympy__sympy__1.9\nconfigfile: pytest.ini\nplugins: anyio-4.3.0\n\n83 passed in 4.87s\n

### Submit the Changes(Require): Submit the changes to the repository.
assistant - Round 8:
Thought and Action(bash_command):
```json
{
    "thought": "All tests have passed successfully and the bug has been fixed. Let's submit the changes to the repository.",
    "bash_command": "submit"
}
```

user - Round 8:
Observation:
Submission successful.
"""

# For executing test suites
TESTING_EXAMPLE = """None"""

MINIMAL_EXAMPLE = """
## Example of a actions trajectory
User Requirement and Issue: Fix the bug in the repo. Because the environment is not available, you DO NOT need to run and modify any existing test case files or add new test case files to ensure that the bug is fixed.

### Locate issue(Require): Locate the issue in the code by searching for the relevant file, function, or class and open the file to view the code.
cd /workspace/django__django_3.0
->
search_dir_and_preview ASCIIUsernameValidator
->
open /workspace/django__django_3.0/django/contrib/auth/validators.py
->
### Fix the Bug(Require): Fix the bug in the code by editing the relevant function, class or code snippet.
edit 10:20 <<EOF
    regex = r'\A[\w.@+-]+\Z'
    message = _( 
        'Enter a valid username. This value may contain only English letters, '
        'numbers, and @/./+/-/_ characters.'
    )
    flags = re.ASCII

@deconstructible
class UnicodeUsernameValidator(validators.RegexValidator):
    regex = r'\A[\w.@+-]+\Z'
EOF
->
### Submit the Changes(Require): Submit the changes to the repository.
submit
"""

INVALID_INPUT_MESSAGE = """
No valid command provided. It seems there was an issue with your input. This could be due to a syntax error, missing arguments, or an unsupported command. Please review your command and try again.

If you have completed the task, please use the `submit` command to finish the task.
"""

# think about if the task of locating the issue has been completed
ONLY_LOCATE_ISSUE_THINK_PROMPT = """
# User Requirement and Issue
{user_requirement_and_issue}

# Context
{context}

Output a json following the format:
```json
{{
    "thought": str = "Thought on current situation, reflect on whether you correctly completed the task of locating the code file with the issue.",
    "state": bool = "Decide whether you need to take more actions to complete the task of locating the code file with the issue. Return true if you think so. Return false if you think the task has been completely fulfilled."
    "location" list = "If state is False, provide the location of the code file with the issue. If state is True, provide an empty list."
}}
```
"""

REFLECTION_PROMPT = """
# Observation
{observation}

# Reflection
```json
{{
    "thought": str = "Thought on current situation, reflect on whether you need to pay attenton to such as syntax error(s) or indention erros",
    "instruction": str = "Give instruction on your next step"
}}
"""
REFINE_EXAMPLES = """
EXAMPLE-1: 
<example>
## Last action
"action": "edit 275:320 <<EOF\n        # Work out the new value for indexes, taking renames into\n        # account\n        indexes = model._meta.indexes\n        if delete_field:\n            indexes = [\n                index for index in indexes if delete_field.name not in index.fields\n            ]\n\n        constraints = list(model._meta.constraints)\n\n        # Provide isolated instances of the fields to the new model body so\n        # that the existing model's internals aren't interfered with when\n        # the dummy model is constructed.\n        body_copy = copy.deepcopy(body)\n\n        # Construct a new model with the new fields to allow self referential\n        # primary key to resolve to. This model won't ever be materialized as a\n        # table and solely exists for foreign key reference resolution purposes.\n        # This wouldn't be required if the schema editor was operating on model\n        # states instead of rendered models.\n        meta_contents = {\n            \"app_label\": model._meta.app_label,\n            \"db_table\": model._meta.db_table,\n            \"unique_together\": unique_together,\n            \"indexes\": indexes,\n            \"constraints\": constraints,\n            \"apps\": apps,\n        }\n        meta = type(\"Meta\", (), meta_contents)\n        body_copy[\"Meta\"] = meta\n        body_copy[\"__module__\"] = model.__module__\n        type(model._meta.object_name, model.__bases__, body_copy)\n\n        # Construct a model with a renamed table name.\n        body_copy = copy.deepcopy(body)\n        meta_contents = {\n            \"app_label\": model._meta.app_label,\n            \"db_table\": \"new__%s\" % strip_quotes(model._meta.db_table),\n            \"unique_together\": unique_together,\n            \"indexes\": indexes,\n            \"constraints\": constraints,\n            \"apps\": apps,\n        }\n        meta = type(\"Meta\", (), meta_contents)\n        body_copy[\"Meta\"] = meta\n        body_copy[\"__module__\"] = model.__module__\n        new_model = type(\"New%s\" % model._meta.object_name, model.__bases__, body_copy)\nEOF",

## Last observation
Your proposed edit has introduced new syntax error(s).
ERRORS:
workspace/django__django_5.0/django/db/backends/sqlite3/schema.py:322:13: E999 IndentationError: unexpected indent

This is how your edit would have looked if applied:
    ...
322:        "indexes": indexes,
323:        "constraints": constraints,
324:        "apps": apps,
325:    }

## Reflection
The previous edit command introduced an indentation error on line 322. I will correct it and ensure the implementation is correct.

## Refine action
```json
{
    "thought": "The previous edit introduced an indentation error on line 322. I need to ensure that the entire block of code is correctly indented and that no unintended lines are modified.",
    "reason": "To correct the previous error and ensure the implementation is correct, we'll focus on modifying only the lines between 275 and 325 as needed. Here is the refined edit command:",
    "bash_command": "edit 275:325 <<EOF\n        ...\n        new_model = type(\"New%s\" % model._meta.object_name, model.__bases__, body_copy)\nEOF"
}
```
</example>
=================================================
EXAMPLE-2: 
<example>
## Last action
"action": "edit 233:236 <<EOF\n    if len(basis) < len(gens):\n        raise NotImplementedError(filldedent('''\n            only zero-dimensional systems supported\n            (finite number of solutions)\n            '''))\nEOF"
# Last observation
> > > > > > Your proposed edit has introduced new syntax error(s). Please understand the fixes and retry your edit command.

ERRORS:
- E999 IndentationError: unexpected indent

This is how your edit would have looked if applied
-------------------------------------------------
[File: workspace/data/test_repo/sympy__sympy__1.9/sympy/solvers/polysys.py (395 lines total)]
(226 more lines above)
227:    def _solve_reduced_system(system, gens, entry=False):
228:        \"""Recursively solves reduced polynomial systems. \"""
229:        if len(system) == len(gens) == 1:
230:            zeros = list(roots(system[0], gens[-1]).keys())
231:            return [(zero,) for zero in zeros]
232:
233:    if len(basis) < len(gens):
234:        raise NotImplementedError(filldedent('''
235:            only zero-dimensional systems supported
236:            (finite number of solutions)
237:            '''))
238:                return []
239:            else:
240:                return None
241:
(154 more lines below)
-------------------------------------------------

This is the original code before your edit
-------------------------------------------------
[File: workspace/data/test_repo/sympy__sympy__1.9/sympy/solvers/polysys.py (394 lines total)]
(227 more lines above)
228:        \"""Recursively solves reduced polynomial systems. \"""
229:        if len(system) == len(gens) == 1:
230:            zeros = list(roots(system[0], gens[-1]).keys())
231:            return [(zero,) for zero in zeros]
232:
233:        basis = groebner(system, gens, polys=True)
234:
235:        if len(basis) == 1 and basis[0].is_ground:
236:            if not entry:
237:                return []
238:            else:
239:                return None
240:
241:        univariate = list(filter(_is_univariate, basis))
(153 more lines below)
-------------------------------------------------
Your changes have NOT been applied. Please fix your edit command and try again.
You either need to 1) Specify the correct start/end line arguments or 2) Correct your edit code.
DO NOT re-run the same failed edit command. Running it again will lead to the same error.

# Reflection
The previous edit command introduced an indentation. I will correct it and ensure the implementation is correct. I should edit in the right line (235:239) and maintain the correct indentation, make sure the code is consistent",

# Refine action
```json
{
    "thought": "It looks like there was an indentation error in the previous edit. Let's correct the indentation and try again.",
    "reason": "To correct the previous error and ensure the implementation is correct, we'll focus on modifying only the lines between  235 and 239 as needed. Here is the refined edit command"
    "bash_command": "\nedit 235:239 <<EOF\n        if len(basis) < len(gens):\n            raise NotImplementedError(filldedent('''\n                only zero-dimensional systems supported\n                (finite number of solutions)\n                '''))\nEOF"
}
```
</example>
=================================================
EXAMPLE-3: 
<example>
## Last action
"action": "edit 616:619 <<EOF\n            indexes = model_state.options.pop(\"index_together\", None)\n            if indexes:\n                model_state.options[\"indexes\"] = indexes\n            order_with_respect_to = model_state.options.pop(\"order_with_respect_to\", None)\nEOF"

## Last observation
Observation:
Your proposed edit has introduced new syntax error(s). Please understand the fixes and retry your edit command.

ERRORS:
- F821 undefined name 'index_together'
- F821 undefined name 'index_together'

This is how your edit would have looked if applied
-------------------------------------------------
[File: workspace/data/test_repo/django__django_5.0/django/db/migrations/autodetector.py (1774 lines total)]
(610 more lines above)
611:            # Are there indexes/unique|index_together to defer?
612:            indexes = model_state.options.pop("indexes")
613:            constraints = model_state.options.pop("constraints")
614:            unique_together = model_state.options.pop("unique_together", None)
615:            # RemovedInDjango51Warning.
616:            indexes = model_state.options.pop("index_together", None)
617:            if indexes:
618:                model_state.options["indexes"] = indexes
619:            order_with_respect_to = model_state.options.pop("order_with_respect_to", None)
620:            # Depend on the deletion of any possible proxy version of us
621:            dependencies = [
622:                (app_label, model_name, None, False),
623:            ]
624:            # Depend on all bases
(1150 more lines below)
-------------------------------------------------

This is the original code before your edit
-------------------------------------------------
[File: workspace/test_repo/django__django_5.0/django/db/migrations/autodetector.py (1774 lines total)]
(610 more lines above)
611:            # Are there indexes/unique|index_together to defer?
612:            indexes = model_state.options.pop("indexes")
613:            constraints = model_state.options.pop("constraints")
614:            unique_together = model_state.options.pop("unique_together", None)
615:            # RemovedInDjango51Warning.
616:            index_together = model_state.options.pop("index_together", None)
617:            order_with_respect_to = model_state.options.pop(
618:                "order_with_respect_to", None
619:            )
620:            # Depend on the deletion of any possible proxy version of us
621:            dependencies = [
622:                (app_label, model_name, None, False),
623:            ]
624:            # Depend on all bases
(1150 more lines below)
-------------------------------------------------
Your changes have NOT been applied. Please fix your edit command and try again.
You either need to 1) Specify the correct start/end line arguments or 2) Correct your edit code.
DO NOT re-run the same failed edit command. Running it again will lead to the same error.


## Reflection
The previous edit failed because 'index_together' was still referenced in the code. To resolve this, I will expand the editing range to include all relevant lines and ensure all references to 'index_together' are replaced with 'indexes'. Let's

## Refine action
```json
{
  "thought": "The previous edit failed because 'index_together' was still referenced in the code. We need to ensure that all references to 'index_together' are replaced with 'indexes'. Let's edit lines 612-619 to replace 'index_together' with 'indexes' and ensure the code is correctly formatted. Additionally, we need to ensure that 'indexes' is properly defined and used in the context. Let's proceed with the edit.",
  "action": "edit 612:619 <<EOF\n            indexes = model_state.options.pop(\"indexes\")\n            constraints = model_state.options.pop(\"constraints\")\n            unique_together = model_state.options.pop(\"unique_together\", None)\n            index_together = model_state.options.pop(\"index_together\", None)\n            if index_together:\n                model_state.options[\"indexes\"] = index_together\n            order_with_respect_to = model_state.options.pop(\"order_with_respect_to\", None)\nEOF"
}
```
</example>
=================================================
"""

REFINE_EDIT_PROMPT = """
Line numbers start from 1.
# Examples
{examples}

# Original Code Lines
{code_lines}

# Last action
{last_action}

# Last observation
The actions in front and what was observed after the last action:
{last_observation}

# Reflection
Provide your thoughts on the observation and action:
{thought}

# Instruction
When editing the code to solve the problem, I encountered the error described in the Last Observation. This error is often due to misremembering the code lines and contents.
Please read the context, including the code block and last edit action, and help me refine the edit action to ensure it is correct.

# Refine action
Please ensure the output of assistant strictly follows the JSON format provided below:
{output_format}
"""

SUMMARY_PROMPT = """
# Current Trajectory
{trajectory}

# Current Code Change
{code_change}

# Summary
Please provide a concise summary based on the information from the trajectory above. Include the main thought, actions, observation, and any significant insights.

```json
{{
    "thought": "Consider the key events, outcomes, action and observations detailed in the trajectory when summarizing.",
    "summary": "Provide a clear and concise summary of the steps taken, progress made, and any notable insights up to this point."
}}
```
"""

REFLECTION_TRAJ_PROMPT = """
# Current Trajectory
{trajectory}

# Current Code Change
{code_change}

# Task
Reflect on the trajectory and find improved steps or methods for the next attempt.

# Response Format
Please ensure the output of the assistant strictly follows the JSON format provided below:

```json
{{
    "thought": "str = Consider the key path, action, and observations detailed in the trajectory. Analyze the reason for the failure. Provide a clear and concise summary of the steps taken, decisions made, and any notable insights up to this point.",
    "plan": "str = Provide a step-by-step plan to optimize the solving process. Include specific actions to take, commands to use, potential obstacles to avoid, and measurable goals to track progress."
}}
```
"""
