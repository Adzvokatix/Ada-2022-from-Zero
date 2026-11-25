# Ada 2022 from Zero: Volume 2

<!-- verify: lesson-folder ~/ada-course-2/lesson-{n} -->

The second half of the course: programs made of many files, files on disk, data structures, pointers, object-oriented types and tasks. It picks up where [Volume 1](../README.md) ends, so work through that first. Every program here went through GNAT 13.3 and gprbuild, and every terminal shows exactly what they printed. Stuck on a word? It's in this volume's [glossary](#glossary), or in [Volume 1's](../README.md#glossary). This first part has lessons 0 to 2; containers, generics, reductions, pointers, tagged types and tasks follow.

**0 of 12 done**

[Lesson 0: Projects](#0)

[Lesson 1: Files and the command line](#1)

[Lesson 2: Discriminants](#2)

[Glossary](#glossary)

# 0

## Projects and gprbuild

Volume 1 built every program with one `gnatmake` command. From now on programs have several files in several folders, so you'll write down how to build them once, in a project file, and let a tool called gprbuild follow it.

### Why a project file

Think back to Volume 1. Every build meant typing `gnatmake -q -gnat2022 -gnata` and a file name, and forgetting `-gnat2022` gave you strange errors. The compiler's leftover `.o` and `.ali` files piled up next to your code. And everything had to live in one folder, because that's where `gnatmake` looked.

Real programs have dozens of files, sorted into folders. A *project file* answers the build questions once, in writing:

- where the Ada files are
- where the compiler's leftovers should go
- where the finished program should go
- which file holds the main procedure
- which switches to use

It's a short text file ending in `.gpr`. *gprbuild* reads it and does the rest. Think of it as the instructions taped to the lid of a toolbox: anyone who opens the folder knows how to put the program together.

Your computer

### 1. Install gprbuild

On Linux

Run the line for your distribution.

Debian, Ubuntu, Mint

```
sudo apt install gprbuild
```

If you used Volume 1's install line, this just says gprbuild is already installed.

Fedora

```
sudo dnf install gprbuild
```

Arch, Manjaro, Garuda

```
paru -S gprbuild
```

On Arch-based systems gprbuild isn't in the official repositories. It comes from the AUR, the collection of packages that users maintain, and `paru` (or `yay -S gprbuild`) builds it for you. That takes a few minutes. When Arch moves to a new major version of GCC, rebuild it the same way.

On Windows

In the **MSYS2 UCRT64** terminal:

MSYS2 UCRT64

```
pacman -S mingw-w64-ucrt-x86_64-gprbuild
```

Press Enter when it asks `Proceed with installation? [Y/n]`.

On Mac

Nothing to do: Volume 1's setup installed gprbuild with `alr install gnat_native gprbuild`.

Then check it worked:

Terminal

```
gprbuild --version
```

**You should see** a first line starting `GPRBUILD`. The output in this volume comes from Ubuntu 24.04's gprbuild package. A newer one may word its progress lines a little differently, but it does the same jobs.

### 2. Make a folder for this lesson

Every lesson in this volume gets its own folder: `lesson-0`, `lesson-1`, and so on. Programs in different lessons share file names, and separate folders keep them apart.

Terminal

```
mkdir -p ~/ada-course-2/lesson-0/src
cd ~/ada-course-2/lesson-0
```

The `src` folder inside it will hold the Ada files.

### 3. Save the program's three files

The program is a package called `Greetings`, with a spec and a body, and a main procedure that uses it, just like Volume 1's lesson 12. This time the Ada files go in `src`. The caption above each box is where to save it.

src/greetings.ads

```
package Greetings is
   procedure Say_Hello (Name : String);
   procedure Say_Goodbye (Name : String);
end Greetings;
```

src/greetings.adb

```
with Ada.Text_IO; use Ada.Text_IO;

package body Greetings is

   procedure Say_Hello (Name : String) is
   begin
      Put_Line ("Hello, " & Name & "!");
   end Say_Hello;

   procedure Say_Goodbye (Name : String) is
   begin
      Put_Line ("Goodbye, " & Name & ".");
   end Say_Goodbye;

end Greetings;
```

src/greet.adb

```
with Greetings;

procedure Greet is
begin
   Greetings.Say_Hello ("Ada");
   Greetings.Say_Goodbye ("Ada");
end Greet;
```

The terminal way from Volume 1 still works: `cat > src/greetings.ads`, paste, Enter, Ctrl+D.

### 4. Write the project file

This one goes in `lesson-0` itself, next to `src`, not inside it.

greet.gpr

```
project Greet is
   for Source_Dirs use ("src");
   for Object_Dir use "obj";
   for Exec_Dir use ".";
   for Main use ("greet.adb");

   package Compiler is
      for Default_Switches ("Ada") use ("-gnat2022", "-gnata", "-gnatwa");
   end Compiler;
end Greet;
```

It looks like Ada, but it isn't: project files have their own small language. `for Something use value;` sets one of the project's settings, which are called *attributes*. Text goes in double quotes, and a list goes in parentheses with commas.

| Line | What it says |
| --- | --- |
| `project Greet is` … `end Greet;` | The project's name. Name the file after it, in lower case: `greet.gpr` |
| `for Source_Dirs use ("src");` | Look for Ada files in the `src` folder. It's a list, so you can name several folders |
| `for Object_Dir use "obj";` | Put the compiler's leftovers here. gprbuild makes the folder for you |
| `for Exec_Dir use ".";` | Put the finished program here. A single dot means "this folder", the one holding `greet.gpr` |
| `for Main use ("greet.adb");` | The file with the main procedure: the one that becomes a program you can run |
| `package Compiler is` … | Switches for the compiler, given once here instead of on every command |
| `-gnatwa` | New: turn on almost all warnings. More on those below |

### 5. Build it and run it

Terminal

```
$ gprbuild -P greet.gpr
Setup
   [mkdir]        object directory for project Greet
Compile
   [Ada]          greet.adb
   [Ada]          greetings.adb
Bind
   [gprbind]      greet.bexch
   [Ada]          greet.ali
Link
   [link]         greet.adb
$ ./greet
Hello, Ada!
Goodbye, Ada.
```

`-P greet.gpr` means "build the project described in `greet.gpr`". gprbuild reports four jobs as it goes:

| Step | What happens |
| --- | --- |
| Setup | Makes the `obj` folder. Only the first time |
| Compile | Turns each `.adb` file into machine code in `obj` |
| Bind | Checks every part was compiled against the same version of each spec, and works out the order the packages start up in |
| Link | Joins all the parts into one program file |

`gnatmake` did the same four jobs. With `-q` it just didn't say so. Add `-q` here too, and gprbuild says nothing unless something is wrong:

Terminal

```
$ gprbuild -q -P greet.gpr
```

Silence again: nothing had changed since the last build, so there was nothing to do. gprbuild only recompiles files that changed, and the files that depend on them.

After the build, the folder looks like this:

lesson-0 after the build

```
lesson-0/
├── greet          the program
├── greet.gpr      the project file
├── obj/           the compiler's leftovers
└── src/
    ├── greet.adb
    ├── greetings.adb
    └── greetings.ads
```

Your code stays in `src`, the clutter stays in `obj`, and the program sits on top. To clear away everything the build made, run `gprclean` on the project:

Terminal

```
$ gprclean -q -P greet.gpr
$ ./greet
bash: ./greet: No such file or directory
$ gprbuild -q -P greet.gpr
$ ./greet
Hello, Ada!
Goodbye, Ada.
```

`gprclean` deleted the program along with the leftovers, so `./greet` failed until the next build. Your shell words that failure its own way: fish, for one, says `Unknown command`.

### Warnings: the compiler's second opinion

An *error* stops the build: something breaks the rules of Ada. A *warning* doesn't stop it. The program still gets built, but the compiler has spotted something that's legal and probably a mistake. `-gnatwa` switches on almost all of them.

Add a variable to `greet.adb` that the program never uses:

src/greet.adb

```
with Greetings;

procedure Greet is
   Visitors : Natural := 0;
begin
   Greetings.Say_Hello ("Ada");
   Greetings.Say_Goodbye ("Ada");
end Greet;
```

Terminal

```
$ gprbuild -q -P greet.gpr
greet.adb:4:04: warning: variable "Visitors" is not referenced [-gnatwu]
```

A warning reads like an error: file, line and column, then the message. The part in square brackets names the switch that turned this warning on, so you can look it up. Here it's right: `Visitors` does nothing. Take it out again, and the build is silent:

src/greet.adb

```
with Greetings;

procedure Greet is
begin
   Greetings.Say_Hello ("Ada");
   Greetings.Say_Goodbye ("Ada");
end Greet;
```

Terminal

```
$ gprbuild -q -P greet.gpr
```

Treat every warning as a question the compiler is asking you. Most of the time, the answer is a fix.

### Child packages

When a package grows, Ada lets you hang another package underneath it, called a *child package*. Its name is the parent's name, a dot, and its own name. Here's `Greetings.Formal`, for more polite occasions:

src/greetings-formal.ads

```
package Greetings.Formal is
   procedure Say_Hello (Title, Surname : String);
end Greetings.Formal;
```

src/greetings-formal.adb

```
with Ada.Text_IO; use Ada.Text_IO;

package body Greetings.Formal is

   procedure Say_Hello (Title, Surname : String) is
   begin
      Put_Line ("Good day, " & Title & " " & Surname & ".");
   end Say_Hello;

end Greetings.Formal;
```

src/greet.adb

```
with Greetings.Formal;

procedure Greet is
begin
   Greetings.Say_Hello ("Ada");
   Greetings.Formal.Say_Hello ("Countess", "Lovelace");
   Greetings.Say_Goodbye ("Ada");
end Greet;
```

Terminal

```
$ gprbuild -q -P greet.gpr
$ ./greet
Hello, Ada!
Good day, Countess Lovelace.
Goodbye, Ada.
```

Four rules come with children:

- **The file name swaps the dot for a hyphen.** `Greetings.Formal` lives in `greetings-formal.ads` and `greetings-formal.adb`. That's GNAT's naming rule.
- **The parent comes along.** `with Greetings.Formal;` makes `Greetings` available too, which is why `greet.adb` could still call `Greetings.Say_Hello`.
- **A child sees its parent.** Inside `Greetings.Formal`, everything in the spec of `Greetings` is usable without a `with` or a `Greetings.` in front.
- **A child can see its parent's private part**, from its own private part and its body. That matters once you have private types to build on.

Two procedures called `Say_Hello` don't clash, because they live in different packages: one is `Greetings.Say_Hello` and the other `Greetings.Formal.Say_Hello`.

Here's what happens with a dot in the file name instead. This renames the spec wrongly, builds, then puts the name back:

Terminal

```
$ mv src/greetings-formal.ads src/greetings.formal.ads
$ gprbuild -q -P greet.gpr
greet.adb:1:06: error: "Greet (body)" depends on "Greetings.Formal (body)"
greet.adb:1:06: error: "Greetings.Formal (body)" depends on "Greetings.Formal (spec)"
greet.adb:1:06: error: file "greetings-formal.ads" not found
gprbuild: *** compilation phase failed
$ mv src/greetings.formal.ads src/greetings-formal.ads
$ gprbuild -q -P greet.gpr
```

Read the error from the bottom up. gprbuild looked for `greetings-formal.ads`, the only name the rule allows, and didn't find it. The two lines above trace why it needed it: `greet.adb` uses `Greetings.Formal`, and that package's body needs its spec.

#### Remember

- A project file (`.gpr`) says where the code is, where the leftovers and the program go, and which switches to use
- Build with `gprbuild -q -P name.gpr`; clear up with `gprclean -P name.gpr`
- Warnings don't stop the build, but read every one
- Child package `Parent.Child` lives in `parent-child.ads` and `parent-child.adb`

#### Common mistakes

- Saving the `.gpr` file inside `src` instead of next to it
- Leaving a folder out of `Source_Dirs`, so gprbuild can't find a file in it
- A dot instead of a hyphen in a child package's file name
- Typing `./greet` while in a different folder from `Exec_Dir`

### Exercises

Exercise 0.1

#### A project for an old program

Here's a two-file program in Volume 1 style. Give it a project of its own: a folder called `temps`, with the Ada files in `temps/src`, leftovers in `temps/obj` and the program in `temps` itself. Start the folder and save the files:

Terminal

```
$ cd ~/ada-course-2/lesson-0
$ mkdir -p temps/src
$ cd temps
```

src/temps.ads

```
package Temps is
   function To_Fahrenheit (Celsius : Float) return Float;
end Temps;
```

src/temps.adb

```
package body Temps is
   function To_Fahrenheit (Celsius : Float) return Float is
   begin
      return Celsius * 9.0 / 5.0 + 32.0;
   end To_Fahrenheit;
end Temps;
```

src/show_temps.adb

```
with Ada.Text_IO;       use Ada.Text_IO;
with Ada.Float_Text_IO; use Ada.Float_Text_IO;
with Temps;

procedure Show_Temps is
   Celsius : Float := 0.0;
begin
   while Celsius <= 100.0 loop
      Put (Celsius, Fore => 3, Aft => 0, Exp => 0);
      Put (" C = ");
      Put (Temps.To_Fahrenheit (Celsius), Fore => 3, Aft => 0, Exp => 0);
      Put_Line (" F");
      Celsius := @ + 25.0;
   end loop;
end Show_Temps;
```

Now write `temps.gpr` and build it.

Target output

```
$ ./show_temps
  0.0 C =  32.0 F
 25.0 C =  77.0 F
 50.0 C = 122.0 F
 75.0 C = 167.0 F
100.0 C = 212.0 F
```

<details>
<summary>Hint</summary>

Copy `greet.gpr` and change the names: the project, its `end`, and the main file. The three folder lines stay the same.

</details>

<details>
<summary>Solution</summary>

temps.gpr

```
project Temps is
   for Source_Dirs use ("src");
   for Object_Dir use "obj";
   for Exec_Dir use ".";
   for Main use ("show_temps.adb");

   package Compiler is
      for Default_Switches ("Ada") use ("-gnat2022", "-gnata", "-gnatwa");
   end Compiler;
end Temps;
```

Terminal

```
$ gprbuild -q -P temps.gpr
$ ./show_temps
  0.0 C =  32.0 F
 25.0 C =  77.0 F
 50.0 C = 122.0 F
 75.0 C = 167.0 F
100.0 C = 212.0 F
```

The project is named `Temps`, after its folder and file, even though the program it builds is `show_temps`. Those don't have to match.

</details>

Exercise 0.2

#### A child that shouts

Add a child package `Greetings.Loud` to the greeting project, with a procedure `Say_Hello (Name : String)` that greets in capital letters. Then make `greet.adb` call it, after the formal greeting.

Target output

```
$ ./greet
Hello, Ada!
Good day, Countess Lovelace.
HELLO, ADA!
Goodbye, Ada.
```

<details>
<summary>Hint</summary>

The files are `src/greetings-loud.ads` and `src/greetings-loud.adb`. `Ada.Characters.Handling.To_Upper` turns a whole String into capitals.

</details>

<details>
<summary>Solution</summary>

Terminal

```
$ cd ~/ada-course-2/lesson-0
```

src/greetings-loud.ads

```
package Greetings.Loud is
   procedure Say_Hello (Name : String);
end Greetings.Loud;
```

src/greetings-loud.adb

```
with Ada.Text_IO;             use Ada.Text_IO;
with Ada.Characters.Handling; use Ada.Characters.Handling;

package body Greetings.Loud is

   procedure Say_Hello (Name : String) is
   begin
      Put_Line (To_Upper ("Hello, " & Name & "!"));
   end Say_Hello;

end Greetings.Loud;
```

src/greet.adb

```
with Greetings.Formal;
with Greetings.Loud;

procedure Greet is
begin
   Greetings.Say_Hello ("Ada");
   Greetings.Formal.Say_Hello ("Countess", "Lovelace");
   Greetings.Loud.Say_Hello ("Ada");
   Greetings.Say_Goodbye ("Ada");
end Greet;
```

Terminal

```
$ gprbuild -q -P greet.gpr
$ ./greet
Hello, Ada!
Good day, Countess Lovelace.
HELLO, ADA!
Goodbye, Ada.
```

`greet.gpr` didn't need to change: the new files are in `src`, which the project already searches.

</details>

Exercise 0.3

#### Silence the warnings

This program works, but `-gnatwa` has three things to say about it. Make a folder `tidy` with a project like `greet.gpr`, build the program, read the warnings, and change the program until the build is silent. It must still print the same thing.

Terminal

```
$ cd ~/ada-course-2/lesson-0
$ mkdir -p tidy/src
$ cd tidy
```

src/tidy.adb

```
with Ada.Text_IO;       use Ada.Text_IO;
with Ada.Strings.Fixed;

procedure Tidy is
   Width : Natural := 20;
   Count : Natural := 0;
begin
   Put_Line ("Width is" & Width'Image);
end Tidy;
```

Target output

```
$ gprbuild -q -P tidy.gpr
$ ./tidy
Width is 20
```

<details>
<summary>Hint</summary>

Build it once and read each warning's last few words. One `with` isn't needed, one variable isn't used, and one variable never changes.

</details>

<details>
<summary>Solution</summary>

tidy.gpr

```
project Tidy is
   for Source_Dirs use ("src");
   for Object_Dir use "obj";
   for Exec_Dir use ".";
   for Main use ("tidy.adb");

   package Compiler is
      for Default_Switches ("Ada") use ("-gnat2022", "-gnata", "-gnatwa");
   end Compiler;
end Tidy;
```

The first build, with the original program:

Terminal

```
$ gprbuild -q -P tidy.gpr
tidy.adb:2:17: warning: unit "Ada.Strings.Fixed" is not referenced [-gnatwu]
tidy.adb:5:04: warning: "Width" is not modified, could be declared constant [-gnatwk]
tidy.adb:6:04: warning: variable "Count" is not referenced [-gnatwu]
```

The fixed program: no `Ada.Strings.Fixed`, no `Count`, and `Width` is a constant because it never changes.

src/tidy.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Tidy is
   Width : constant Natural := 20;
begin
   Put_Line ("Width is" & Width'Image);
end Tidy;
```

Terminal

```
$ gprbuild -q -P tidy.gpr
$ ./tidy
Width is 20
```

</details>

Exercise 0.4

#### Two programs, one project

`Main` takes a list. Add a second program to the greeting project, `src/wave.adb`, which only says goodbye to Grace. Build both with one command.

Target output

```
$ gprbuild -q -P greet.gpr
$ ./greet
Hello, Ada!
Good day, Countess Lovelace.
HELLO, ADA!
Goodbye, Ada.
$ ./wave
Goodbye, Grace.
```

<details>
<summary>Hint</summary>

`for Main use ("greet.adb", "wave.adb");`

</details>

<details>
<summary>Solution</summary>

Terminal

```
$ cd ~/ada-course-2/lesson-0
```

src/wave.adb

```
with Greetings;

procedure Wave is
begin
   Greetings.Say_Goodbye ("Grace");
end Wave;
```

greet.gpr

```
project Greet is
   for Source_Dirs use ("src");
   for Object_Dir use "obj";
   for Exec_Dir use ".";
   for Main use ("greet.adb", "wave.adb");

   package Compiler is
      for Default_Switches ("Ada") use ("-gnat2022", "-gnata", "-gnatwa");
   end Compiler;
end Greet;
```

Terminal

```
$ gprbuild -q -P greet.gpr
$ ./greet
Hello, Ada!
Good day, Countess Lovelace.
HELLO, ADA!
Goodbye, Ada.
$ ./wave
Goodbye, Grace.
```

`greetings.adb` was compiled once and used by both programs.

</details>

# 1

## Files and the command line

So far your programs have learned everything from the keyboard and forgotten it when they ended. This lesson gives them two new ways in: words typed after the program's name, and files on disk. Files are also a way out, and they outlast the program.

### This lesson's folder and project

From here on, every lesson starts the same way: a folder, and a small project file in it.

Terminal

```
$ mkdir -p ~/ada-course-2/lesson-1
$ cd ~/ada-course-2/lesson-1
```

lesson_1.gpr

```
project Lesson_1 is
   for Object_Dir use "obj";
   for Exec_Dir use ".";

   package Compiler is
      for Default_Switches ("Ada") use ("-gnat2022", "-gnata", "-gnatwa");
   end Compiler;
end Lesson_1;
```

There's no `Source_Dirs` line, so gprbuild looks for Ada files in the project's own folder. There's no `Main` either: this lesson has several programs, and you'll name the one to build each time, like `gprbuild -q args.adb`. And there's no `-P`: when a folder holds exactly one `.gpr` file, gprbuild uses it without being told.

### Arguments: the words after the program's name

You've been doing this all along: in `gprbuild -q args.adb`, the words `-q` and `args.adb` are *command-line arguments*, handed to gprbuild when it starts. Your own programs can read theirs with the package `Ada.Command_Line`:

args.adb

```
with Ada.Text_IO;      use Ada.Text_IO;
with Ada.Command_Line; use Ada.Command_Line;

procedure Args is
begin
   Put_Line ("Program name: " & Command_Name);
   Put_Line ("Arguments:" & Argument_Count'Image);
   for I in 1 .. Argument_Count loop
      Put_Line (I'Image & ": " & Argument (I));
   end loop;
end Args;
```

Terminal

```
$ gprbuild -q args.adb
$ ./args
Program name: ./args
Arguments: 0
$ ./args red green
Program name: ./args
Arguments: 2
 1: red
 2: green
$ ./args "two words" 3
Program name: ./args
Arguments: 2
 1: two words
 2: 3
```

| Name | What it gives you |
| --- | --- |
| `Argument_Count` | How many arguments there are: a Natural, 0 if none |
| `Argument (I)` | Argument number `I`, counting from 1, as a String |
| `Command_Name` | How the program was started, here `./args` |

The shell splits what you type at the spaces, so `red green` is two arguments. Quotes keep words together, and the quotes themselves aren't passed on: the first argument in the last run was `two words`. Every argument is a String, even `3`. To use it as a number, convert it with `Integer'Value (Argument (2))`, as in Volume 1's lesson 4.

Asking for an argument that isn't there, like `Argument (1)` when `Argument_Count` is 0, raises Constraint_Error. Check the count first.

### Exit status: telling the shell how it went

When a program ends, it hands the shell a number called its *exit status*. 0 means it worked; anything else means something went wrong. Scripts and other programs check it. Here's a program that adds up the numbers it's given, and refuses politely when there aren't any:

sum.adb

```
with Ada.Text_IO;      use Ada.Text_IO;
with Ada.Command_Line; use Ada.Command_Line;

procedure Sum is
   Total : Integer := 0;
begin
   if Argument_Count = 0 then
      Put_Line (Standard_Error, "usage: sum NUMBER...");
      Set_Exit_Status (Failure);
      return;
   end if;
   for I in 1 .. Argument_Count loop
      Total := @ + Integer'Value (Argument (I));
   end loop;
   Put_Line (Total'Image);
end Sum;
```

Terminal

```
$ gprbuild -q sum.adb
$ ./sum 3 4 5
 12
$ ./sum; echo "exit status: $?"
usage: sum NUMBER...
exit status: 1
```

Three new things here:

- `Set_Exit_Status (Failure)` sets the number the program will hand back. `Failure` and `Success` are constants in `Ada.Command_Line`.
- `return;` leaves the procedure straight away. In the main procedure, that ends the program.
- `Standard_Error` is a second way out to the screen, meant for complaints. `Put_Line (Standard_Error, …)` sends a line there instead of to normal output.

`$?` holds the exit status of the last command in bash, zsh and MSYS2's terminal. In fish, it's `$status`: `./sum; echo "exit status: $status"`.

Why two outputs? Because you can send normal output into a file with `>`, and complaints still reach you:

Terminal

```
$ ./sum 10 20 > total.txt
$ cat total.txt
 30
$ ./sum > total.txt
usage: sum NUMBER...
$ cat total.txt
```

The second run's complaint went to the screen, not into `total.txt`. Its normal output was empty, so `>` left `total.txt` empty.

### Reading a file

Here's a file to read. Save it in `lesson-1`:

notes.txt

```
Ada is named after Ada Lovelace.
She wrote the first published program, in 1843.
The language was designed for programs that must not fail.
Its first standard came out in 1983.
```

This program counts the lines in a file and finds the longest:

line_stats.adb

```
with Ada.Text_IO;      use Ada.Text_IO;
with Ada.Command_Line; use Ada.Command_Line;

procedure Line_Stats is
   File    : File_Type;
   Lines   : Natural := 0;
   Longest : Natural := 0;
begin
   Open (File, In_File, Argument (1));
   while not End_Of_File (File) loop
      declare
         Line : constant String := Get_Line (File);
      begin
         Lines   := @ + 1;
         Longest := Natural'Max (Longest, Line'Length);
      end;
   end loop;
   Close (File);
   Put_Line (Argument (1) & ":" & Lines'Image & " lines, the longest has"
             & Longest'Image & " characters");
end Line_Stats;
```

Terminal

```
$ gprbuild -q line_stats.adb
$ ./line_stats notes.txt
notes.txt: 4 lines, the longest has 58 characters
```

Line by line:

| Code | What it does |
| --- | --- |
| `File : File_Type;` | A *file handle*: a variable that stands for one open file. It isn't the file itself, just your grip on it |
| `Open (File, In_File, Argument (1));` | Find the file with that name and connect it to `File`. `In_File` means for reading |
| `End_Of_File (File)` | True once every line has been read |
| `Get_Line (File)` | The next line from the file, without its line ending |
| `Close (File);` | Let go of the file. `File` can then be opened again, on any file |

Every `Ada.Text_IO` subprogram you know has a twin that takes a file first: `Get_Line (File)`, `Put_Line (File, "text")`, `New_Line (File)`. Without the file, they use the keyboard and screen, as before.

### When the file isn't there

Terminal

```
$ ./line_stats nothing.txt

raised ADA.IO_EXCEPTIONS.NAME_ERROR : nothing.txt: No such file or directory
$ ./line_stats

raised CONSTRAINT_ERROR : a-comlin.adb:61 explicit raise
```

Two different exceptions. With a missing file, `Open` raises `Name_Error`. With no argument at all, `Argument (1)` raises Constraint_Error before `Open` even runs. That message points at `a-comlin.adb`, which is GNAT's own file for `Ada.Command_Line`: the exception was raised in there, on your behalf. These are the exceptions from file work, all in `Ada.Text_IO`:

| Exception | Raised when |
| --- | --- |
| `Name_Error` | There's no file with that name, or the name isn't allowed |
| `Use_Error` | The file is there but can't be used that way, for example you don't have permission |
| `End_Error` | You read past the end of the file |
| `Status_Error` | The handle is in the wrong state: opening one that's already open, or reading from one that's closed |

A program meant for other people should check the arguments first and handle the rest, with Volume 1's lesson 13:

line_stats.adb

```
with Ada.Text_IO;      use Ada.Text_IO;
with Ada.Command_Line; use Ada.Command_Line;

procedure Line_Stats is
   File    : File_Type;
   Lines   : Natural := 0;
   Longest : Natural := 0;
begin
   if Argument_Count /= 1 then
      Put_Line (Standard_Error, "usage: line_stats FILE");
      Set_Exit_Status (Failure);
      return;
   end if;
   Open (File, In_File, Argument (1));
   while not End_Of_File (File) loop
      declare
         Line : constant String := Get_Line (File);
      begin
         Lines   := @ + 1;
         Longest := Natural'Max (Longest, Line'Length);
      end;
   end loop;
   Close (File);
   Put_Line (Argument (1) & ":" & Lines'Image & " lines, the longest has"
             & Longest'Image & " characters");
exception
   when Name_Error =>
      Put_Line (Standard_Error, "line_stats: can't find " & Argument (1));
      Set_Exit_Status (Failure);
end Line_Stats;
```

Terminal

```
$ gprbuild -q line_stats.adb
$ ./line_stats nothing.txt
line_stats: can't find nothing.txt
$ ./line_stats
usage: line_stats FILE
$ ./line_stats notes.txt
notes.txt: 4 lines, the longest has 58 characters
```

### Writing a file

There are two ways to get a file ready for writing:

| Call | What it does |
| --- | --- |
| `Create (File, Out_File, Name);` | Makes a new, empty file. If one with that name exists, it's **emptied first** |
| `Open (File, Append_File, Name);` | Opens a file that already exists, ready to add lines to the end |

This to-do list program uses both, and `Ada.Directories.Exists` to pick between them:

todo.adb

```
with Ada.Text_IO;      use Ada.Text_IO;
with Ada.Command_Line; use Ada.Command_Line;
with Ada.Directories;

procedure Todo is
   List_Name : constant String := "todo.txt";
   File      : File_Type;
begin
   if Argument_Count = 2 and then Argument (1) = "add" then
      if Ada.Directories.Exists (List_Name) then
         Open (File, Append_File, List_Name);
      else
         Create (File, Out_File, List_Name);
      end if;
      Put_Line (File, Argument (2));
      Close (File);
      Put_Line ("Added: " & Argument (2));

   elsif Argument_Count = 1 and then Argument (1) = "list" then
      if Ada.Directories.Exists (List_Name) then
         Open (File, In_File, List_Name);
         for Number in Positive loop
            exit when End_Of_File (File);
            Put_Line (Number'Image & ". " & Get_Line (File));
         end loop;
         Close (File);
      else
         Put_Line ("Nothing to do.");
      end if;

   else
      Put_Line (Standard_Error, "usage: todo add ""THING"" | todo list");
      Set_Exit_Status (Failure);
   end if;
end Todo;
```

Terminal

```
$ gprbuild -q todo.adb
$ ./todo list
Nothing to do.
$ ./todo add "Buy flour"
Added: Buy flour
$ ./todo add "Read lesson 2"
Added: Read lesson 2
$ ./todo list
 1. Buy flour
 2. Read lesson 2
$ cat todo.txt
Buy flour
Read lesson 2
```

The list survives after the program ends: it's in `todo.txt`, which `cat` shows as plain lines. `for Number in Positive loop` counts 1, 2, 3 and so on with no planned end; the `exit when` stops it when the file runs out. Inside a String, `""` stands for one `"` character, so the usage message shows real quote marks.

`Ada.Directories` has more for working with files and folders as a whole: `Delete_File`, `Rename`, `Size`, `Create_Directory`.

#### Remember

- `Argument_Count` and `Argument (I)` come from `Ada.Command_Line`; every argument is a String
- Set `Set_Exit_Status (Failure)` and write to `Standard_Error` when something goes wrong
- `Open (File, In_File, …)` to read, `Create (File, Out_File, …)` to start fresh, `Open (File, Append_File, …)` to add
- Read with `while not End_Of_File (File) loop … Get_Line (File) … end loop;`, then `Close (File);`

#### Common mistakes

- Calling `Argument (1)` without checking `Argument_Count` first
- Using `Create` on a file you meant to add to: it starts empty again
- Calling `Get_Line (File)` after `End_Of_File (File)` is True: End_Error
- Opening a handle that's already open: Status_Error

### Exercises

Exercise 1.1

#### Hello, everyone

Write `hello_all`, which greets everyone named on its command line. Run with no names, it should complain to standard error and finish with exit status 1.

Target output

```
$ ./hello_all Ada Grace Linus
Hello, Ada!
Hello, Grace!
Hello, Linus!
$ ./hello_all; echo "exit status: $?"
usage: hello_all NAME...
exit status: 1
```

<details>
<summary>Hint</summary>

Use the start of `sum.adb` for the no-arguments case, then a `for` loop from 1 to `Argument_Count`.

</details>

<details>
<summary>Solution</summary>

hello_all.adb

```
with Ada.Text_IO;      use Ada.Text_IO;
with Ada.Command_Line; use Ada.Command_Line;

procedure Hello_All is
begin
   if Argument_Count = 0 then
      Put_Line (Standard_Error, "usage: hello_all NAME...");
      Set_Exit_Status (Failure);
      return;
   end if;
   for I in 1 .. Argument_Count loop
      Put_Line ("Hello, " & Argument (I) & "!");
   end loop;
end Hello_All;
```

Terminal

```
$ gprbuild -q hello_all.adb
$ ./hello_all Ada Grace Linus
Hello, Ada!
Hello, Grace!
Hello, Linus!
$ ./hello_all; echo "exit status: $?"
usage: hello_all NAME...
exit status: 1
```

</details>

Exercise 1.2

#### Number the lines

Write `number`, which prints a file with a line number in front of each line, right-aligned in three places. Save this list next to it to try it on:

shopping.txt

```
eggs
flour
milk
butter
sugar
lemons
```

Target output

```
$ ./number shopping.txt
  1  eggs
  2  flour
  3  milk
  4  butter
  5  sugar
  6  lemons
```

<details>
<summary>Hint</summary>

`Ada.Integer_Text_IO.Put (Number, Width => 3)` prints a number padded on the left to 3 characters. Then two spaces, then the line.

</details>

<details>
<summary>Solution</summary>

number.adb

```
with Ada.Text_IO;         use Ada.Text_IO;
with Ada.Integer_Text_IO; use Ada.Integer_Text_IO;
with Ada.Command_Line;    use Ada.Command_Line;

procedure Number is
   File  : File_Type;
   Count : Natural := 0;
begin
   if Argument_Count /= 1 then
      Put_Line (Standard_Error, "usage: number FILE");
      Set_Exit_Status (Failure);
      return;
   end if;
   Open (File, In_File, Argument (1));
   while not End_Of_File (File) loop
      Count := @ + 1;
      Put (Count, Width => 3);
      Put_Line ("  " & Get_Line (File));
   end loop;
   Close (File);
end Number;
```

Terminal

```
$ gprbuild -q number.adb
$ ./number shopping.txt
  1  eggs
  2  flour
  3  milk
  4  butter
  5  sugar
  6  lemons
```

</details>

Exercise 1.3

#### Count the words

Write `word_count`, which reports how many lines, words and characters a file has. A word is a run of characters with no spaces in it. Don't count the line endings as characters.

Target output

```
$ ./word_count notes.txt
lines: 4  words: 31  characters: 173
```

<details>
<summary>Hint</summary>

For each line, walk through its characters. A word starts wherever a character that isn't a space comes right after a space, or at the very start of the line. A Boolean `In_Word` keeps track of which side you're on.

</details>

<details>
<summary>Solution</summary>

word_count.adb

```
with Ada.Text_IO;      use Ada.Text_IO;
with Ada.Command_Line; use Ada.Command_Line;

procedure Word_Count is
   File                 : File_Type;
   Lines, Words, Chars  : Natural := 0;
begin
   if Argument_Count /= 1 then
      Put_Line (Standard_Error, "usage: word_count FILE");
      Set_Exit_Status (Failure);
      return;
   end if;
   Open (File, In_File, Argument (1));
   while not End_Of_File (File) loop
      declare
         Line    : constant String := Get_Line (File);
         In_Word : Boolean := False;
      begin
         Lines := @ + 1;
         Chars := @ + Line'Length;
         for C of Line loop
            if C = ' ' then
               In_Word := False;
            elsif not In_Word then
               In_Word := True;
               Words := @ + 1;
            end if;
         end loop;
      end;
   end loop;
   Close (File);
   Put_Line ("lines:" & Lines'Image & "  words:" & Words'Image
             & "  characters:" & Chars'Image);
end Word_Count;
```

Terminal

```
$ gprbuild -q word_count.adb
$ ./word_count notes.txt
lines: 4  words: 31  characters: 173
```

</details>

Exercise 1.4

#### Shout a file

Write `shout`, which copies one file into another with every letter in capitals: `./shout notes.txt loud.txt`. If the first file doesn't exist, say so on standard error and leave the second file alone.

Target output

```
$ ./shout notes.txt loud.txt
Wrote loud.txt
$ cat loud.txt
ADA IS NAMED AFTER ADA LOVELACE.
SHE WROTE THE FIRST PUBLISHED PROGRAM, IN 1843.
THE LANGUAGE WAS DESIGNED FOR PROGRAMS THAT MUST NOT FAIL.
ITS FIRST STANDARD CAME OUT IN 1983.
$ ./shout missing.txt out.txt
shout: can't find missing.txt
```

<details>
<summary>Hint</summary>

Two handles: one opened with `In_File`, one made with `Create`. Open the input first, so a missing input fails before anything is created. `To_Upper` from `Ada.Characters.Handling` works on a whole String.

</details>

<details>
<summary>Solution</summary>

shout.adb

```
with Ada.Text_IO;             use Ada.Text_IO;
with Ada.Command_Line;        use Ada.Command_Line;
with Ada.Characters.Handling; use Ada.Characters.Handling;

procedure Shout is
   Input, Output : File_Type;
begin
   if Argument_Count /= 2 then
      Put_Line (Standard_Error, "usage: shout IN_FILE OUT_FILE");
      Set_Exit_Status (Failure);
      return;
   end if;
   Open (Input, In_File, Argument (1));
   Create (Output, Out_File, Argument (2));
   while not End_Of_File (Input) loop
      Put_Line (Output, To_Upper (Get_Line (Input)));
   end loop;
   Close (Input);
   Close (Output);
   Put_Line ("Wrote " & Argument (2));
exception
   when Name_Error =>
      Put_Line (Standard_Error, "shout: can't find " & Argument (1));
      Set_Exit_Status (Failure);
end Shout;
```

Terminal

```
$ gprbuild -q shout.adb
$ ./shout notes.txt loud.txt
Wrote loud.txt
$ cat loud.txt
ADA IS NAMED AFTER ADA LOVELACE.
SHE WROTE THE FIRST PUBLISHED PROGRAM, IN 1843.
THE LANGUAGE WAS DESIGNED FOR PROGRAMS THAT MUST NOT FAIL.
ITS FIRST STANDARD CAME OUT IN 1983.
$ ./shout missing.txt out.txt
shout: can't find missing.txt
$ ls out.txt
ls: cannot access 'out.txt': No such file or directory
```

`out.txt` was never made: `Open` failed before `Create` ran.

</details>

# 2

## Discriminants and variant records

In Volume 1 every record had a fixed shape: the same fields, the same sizes, every time. This lesson's records shape themselves, using a value you give when you create them.

### This lesson's folder and project

Terminal

```
$ mkdir -p ~/ada-course-2/lesson-2
$ cd ~/ada-course-2/lesson-2
```

lesson_2.gpr

```
project Lesson_2 is
   for Object_Dir use "obj";
   for Exec_Dir use ".";

   package Compiler is
      for Default_Switches ("Ada") use ("-gnat2022", "-gnata", "-gnatwa");
   end Compiler;
end Lesson_2;
```

### A record that sets its own size

A String field in a record needs a size, and in Volume 1 you had to pick one: `Name : String (1 .. 20)`. Too long wastes space and needs padding; too short and some names don't fit. A *discriminant* lets each record choose:

tags.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Tags is

   type Name_Tag (Length : Natural) is record
      Text : String (1 .. Length);
   end record;

   function Make_Tag (Text : String) return Name_Tag is
     ((Length => Text'Length, Text => Text));

   procedure Show (Tag : Name_Tag) is
      Edge : constant String := [1 .. Tag.Length + 2 => '-'];
   begin
      Put_Line ("+" & Edge & "+");
      Put_Line ("| " & Tag.Text & " |");
      Put_Line ("+" & Edge & "+");
   end Show;

   Short : constant Name_Tag := Make_Tag ("Ada");
   Long  : constant Name_Tag := Make_Tag ("Grace Hopper");

begin
   Show (Short);
   Show (Long);
   Put_Line ("Lengths:" & Short.Length'Image & Long.Length'Image);
end Tags;
```

Terminal

```
$ gprbuild -q tags.adb
$ ./tags
+-----+
| Ada |
+-----+
+--------------+
| Grace Hopper |
+--------------+
Lengths: 3 12
```

`Length` sits in parentheses after the type's name, so it's a discriminant: a field you fill in when the record is created, which the rest of the record can depend on. Here it decides how long `Text` is. `Short` holds 3 characters and `Long` holds 12, and both are `Name_Tag`s.

You read a discriminant like any field, `Tag.Length`. You fill it in like any field too, in the aggregate: `(Length => Text'Length, Text => Text)`. The two parts must agree: `Text` must have exactly `Length` characters.

`[1 .. Tag.Length + 2 => '-']` is an array aggregate with a range: positions 1 up to `Tag.Length + 2`, every one a `'-'`. It makes the border exactly fit the name.

### A discriminant is fixed for life

Once a record exists, its discriminant can't change on its own. Try it:

tags_fixed.adb

```
procedure Tags_Fixed is

   type Name_Tag (Length : Natural) is record
      Text : String (1 .. Length);
   end record;

   Tag : Name_Tag := (Length => 3, Text => "Ada");

begin
   Tag.Length := 5;
end Tags_Fixed;
```

Terminal

```
$ gprbuild -q tags_fixed.adb
tags_fixed.adb:10:07: error: assignment to discriminant not allowed
gprbuild: *** compilation phase failed
```

What about replacing the whole record with a longer one? That compiles, but fails when it runs:

tags_swap.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Tags_Swap is

   type Name_Tag (Length : Natural) is record
      Text : String (1 .. Length);
   end record;

   function Make_Tag (Text : String) return Name_Tag is
     ((Length => Text'Length, Text => Text));

   Tag : Name_Tag := Make_Tag ("Ada");

begin
   Put_Line (Tag.Text);
   Tag := Make_Tag ("Grace");
   Put_Line (Tag.Text);
end Tags_Swap;
```

Terminal

```
$ gprbuild -q tags_swap.adb
$ ./tags_swap
Ada

raised CONSTRAINT_ERROR : tags_swap.adb:16 discriminant check failed
```

`Tag` was created with `Length` 3, so it has room for 3 characters, for good. A 5-character tag doesn't fit, and Ada stops with a *discriminant check*, a run-time check that a record's discriminant is the one expected. A variable like this is called *constrained*: its discriminant is set and stays set.

### A default makes a record changeable

Give the discriminant a default value, and a variable declared without one becomes *unconstrained*: whole-record assignments may change its discriminant. The catch: the compiler must set aside enough room for the biggest record it could ever hold. With `Natural`, that's more than two billion characters, and GNAT says so:

tags_flex.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Tags_Flex is

   type Flexible_Tag (Length : Natural := 0) is record
      Text : String (1 .. Length);
   end record;

   Tag : Flexible_Tag;

begin
   Tag := (Length => 3, Text => "Ada");
   Put_Line (Tag.Text);
end Tags_Flex;
```

Terminal

```
$ gprbuild -q tags_flex.adb
tags_flex.adb:5:09: warning: creation of "Flexible_Tag" object may raise Storage_Error [enabled by default]
```

The fix is a small range for the discriminant, so the biggest possible record is small too:

tags_flex.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Tags_Flex is

   subtype Tag_Length is Natural range 0 .. 30;

   type Flexible_Tag (Length : Tag_Length := 0) is record
      Text : String (1 .. Length);
   end record;

   function Make_Tag (Text : String) return Flexible_Tag is
     ((Length => Text'Length, Text => Text));

   Tag : Flexible_Tag;

begin
   Put_Line ("Empty tag, length" & Tag.Length'Image);
   Tag := Make_Tag ("Ada");
   Put_Line (Tag.Text & ", length" & Tag.Length'Image);
   Tag := Make_Tag ("Grace Hopper");
   Put_Line (Tag.Text & ", length" & Tag.Length'Image);
end Tags_Flex;
```

Terminal

```
$ gprbuild -q tags_flex.adb
$ ./tags_flex
Empty tag, length 0
Ada, length 3
Grace Hopper, length 12
```

`Tag` started out empty, with the default length 0, then held 3 characters, then 12. Each time, the whole record was replaced. `Tag.Length := 5;` on its own is still not allowed.

| Discriminant | Variable declared without a value | Can it change? |
| --- | --- | --- |
| No default: `(Length : Natural)` | Not allowed: you must give a value | No, it's constrained |
| With a default: `(Length : Tag_Length := 0)` | Gets the default | Yes, by assigning a whole record |

### Variant records: one type, several shapes

A discriminant can also choose which fields a record has. A circle needs a radius; a rectangle needs a width and a height. One type can hold either:

shapes.adb

```
with Ada.Text_IO;       use Ada.Text_IO;
with Ada.Float_Text_IO; use Ada.Float_Text_IO;
with Ada.Numerics;

procedure Shapes is

   type Shape_Kind is (Circle, Rectangle);

   type Shape (Kind : Shape_Kind) is record
      case Kind is
         when Circle =>
            Radius : Float;
         when Rectangle =>
            Width, Height : Float;
      end case;
   end record;

   function Area (S : Shape) return Float is
   begin
      case S.Kind is
         when Circle =>
            return Ada.Numerics.Pi * S.Radius ** 2;
         when Rectangle =>
            return S.Width * S.Height;
      end case;
   end Area;

   procedure Report (S : Shape) is
   begin
      Put (Shape_Kind'Image (S.Kind) & " area: ");
      Put (Area (S), Fore => 1, Aft => 2, Exp => 0);
      New_Line;
   end Report;

   Wheel : constant Shape := (Kind => Circle, Radius => 1.0);
   Door  : constant Shape := (Kind => Rectangle, Width => 0.9, Height => 2.0);

begin
   Report (Wheel);
   Report (Door);
end Shapes;
```

Terminal

```
$ gprbuild -q shapes.adb
$ ./shapes
CIRCLE area: 3.14
RECTANGLE area: 1.80
```

This is a *variant record*. The `case Kind is` inside the record says which fields exist for each value of `Kind`. A circle has `Radius` and nothing else; a rectangle has `Width` and `Height`. `Area` uses an ordinary `case` statement on the same discriminant to pick the formula.

A few rules:

- The `case` must be the last thing in the record. Fields every shape has go before it.
- Every value of the discriminant needs a `when`, as in a `case` statement. `when others => null;` is allowed, for "no extra fields".
- Each field name may appear only once in the whole record, even in different variants. A rectangle and a triangle can't both have a field called `Height`.

### Asking for a field that isn't there

`Door` is a rectangle. What happens if the program asks for its radius?

wrong_field.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Wrong_Field is

   type Shape_Kind is (Circle, Rectangle);

   type Shape (Kind : Shape_Kind) is record
      case Kind is
         when Circle =>
            Radius : Float;
         when Rectangle =>
            Width, Height : Float;
      end case;
   end record;

   procedure Show_Radius (S : Shape) is
   begin
      Put_Line ("Radius:" & S.Radius'Image);
   end Show_Radius;

   Door : constant Shape := (Kind => Rectangle, Width => 0.9, Height => 2.0);

begin
   Show_Radius (Door);
end Wrong_Field;
```

Terminal

```
$ gprbuild -q wrong_field.adb
$ ./wrong_field

raised CONSTRAINT_ERROR : wrong_field.adb:18 discriminant check failed
```

The same discriminant check stops it. Ada never lets you read a field the record doesn't have, which in some languages quietly gives you whatever bytes happen to be there.

### The compiler checks every shape is handled

Add a triangle to `shapes.adb`: a new value in `Shape_Kind` and its fields in the record, but nothing else yet.

shapes.adb

```
with Ada.Text_IO;       use Ada.Text_IO;
with Ada.Float_Text_IO; use Ada.Float_Text_IO;
with Ada.Numerics;

procedure Shapes is

   type Shape_Kind is (Circle, Rectangle, Triangle);

   type Shape (Kind : Shape_Kind) is record
      case Kind is
         when Circle =>
            Radius : Float;
         when Rectangle =>
            Width, Height : Float;
         when Triangle =>
            Base, Altitude : Float;
      end case;
   end record;

   function Area (S : Shape) return Float is
   begin
      case S.Kind is
         when Circle =>
            return Ada.Numerics.Pi * S.Radius ** 2;
         when Rectangle =>
            return S.Width * S.Height;
      end case;
   end Area;

   procedure Report (S : Shape) is
   begin
      Put (Shape_Kind'Image (S.Kind) & " area: ");
      Put (Area (S), Fore => 1, Aft => 2, Exp => 0);
      New_Line;
   end Report;

   Wheel : constant Shape := (Kind => Circle, Radius => 1.0);
   Door  : constant Shape := (Kind => Rectangle, Width => 0.9, Height => 2.0);

begin
   Report (Wheel);
   Report (Door);
end Shapes;
```

Terminal

```
$ gprbuild -q shapes.adb
shapes.adb:22:07: error: missing case value: "Triangle"
gprbuild: *** compilation phase failed
```

The compiler found the one place that doesn't handle triangles yet. In a big program, that list of places is exactly what you need. That's a good reason to avoid `when others` in a `case` on a kind: with it, the compiler would have stayed quiet. Exercise 2.2 finishes the job.

### Variant records or tagged types?

Variant records are the right tool when you know every kind up front, and you're the one who'd add a new one. Later in this volume, *tagged types* handle "kinds of things" the other way round: anyone can add a new kind without touching the existing code. Each has its place, and you'll see both.

#### Remember

- A discriminant is a field, set when the record is made, that the rest of the record can depend on
- Without a default, a variable's discriminant is fixed for life; with one, a whole-record assignment can change it
- Give a defaulted discriminant a small range, because the compiler makes room for the biggest record
- A variant record's `case` picks the fields; reading a field the record doesn't have raises Constraint_Error

#### Common mistakes

- Assigning to the discriminant alone, like `Tag.Length := 5;`
- An aggregate whose String doesn't have exactly `Length` characters
- A defaulted discriminant of type Natural or Integer: the compiler warns about Storage_Error
- Using one field name in two variants

### Exercises

Exercise 2.1

#### Name badges

Write `badges`, which prints a name tag, as in `tags.adb`, for each name on its command line.

Target output

```
$ ./badges Ada "Grace Hopper" Linus
+-----+
| Ada |
+-----+
+--------------+
| Grace Hopper |
+--------------+
+-------+
| Linus |
+-------+
```

<details>
<summary>Hint</summary>

Keep `Name_Tag`, `Make_Tag` and `Show` from `tags.adb`, and call `Show (Make_Tag (Argument (I)))` in a loop over the arguments.

</details>

<details>
<summary>Solution</summary>

badges.adb

```
with Ada.Text_IO;      use Ada.Text_IO;
with Ada.Command_Line; use Ada.Command_Line;

procedure Badges is

   type Name_Tag (Length : Natural) is record
      Text : String (1 .. Length);
   end record;

   function Make_Tag (Text : String) return Name_Tag is
     ((Length => Text'Length, Text => Text));

   procedure Show (Tag : Name_Tag) is
      Edge : constant String := [1 .. Tag.Length + 2 => '-'];
   begin
      Put_Line ("+" & Edge & "+");
      Put_Line ("| " & Tag.Text & " |");
      Put_Line ("+" & Edge & "+");
   end Show;

begin
   for I in 1 .. Argument_Count loop
      Show (Make_Tag (Argument (I)));
   end loop;
end Badges;
```

Terminal

```
$ gprbuild -q badges.adb
$ ./badges Ada "Grace Hopper" Linus
+-----+
| Ada |
+-----+
+--------------+
| Grace Hopper |
+--------------+
+-------+
| Linus |
+-------+
```

</details>

Exercise 2.2

#### Finish the triangle

Make the triangle version of `shapes.adb` compile, and report a triangle with base 3.0 and altitude 4.0. A triangle's area is half its base times its altitude.

Target output

```
$ ./shapes
CIRCLE area: 3.14
RECTANGLE area: 1.80
TRIANGLE area: 6.00
```

<details>
<summary>Hint</summary>

The compiler already said where: `Area` needs `when Triangle =>`. Then add a third constant and a third `Report`.

</details>

<details>
<summary>Solution</summary>

shapes.adb

```
with Ada.Text_IO;       use Ada.Text_IO;
with Ada.Float_Text_IO; use Ada.Float_Text_IO;
with Ada.Numerics;

procedure Shapes is

   type Shape_Kind is (Circle, Rectangle, Triangle);

   type Shape (Kind : Shape_Kind) is record
      case Kind is
         when Circle =>
            Radius : Float;
         when Rectangle =>
            Width, Height : Float;
         when Triangle =>
            Base, Altitude : Float;
      end case;
   end record;

   function Area (S : Shape) return Float is
   begin
      case S.Kind is
         when Circle =>
            return Ada.Numerics.Pi * S.Radius ** 2;
         when Rectangle =>
            return S.Width * S.Height;
         when Triangle =>
            return S.Base * S.Altitude / 2.0;
      end case;
   end Area;

   procedure Report (S : Shape) is
   begin
      Put (Shape_Kind'Image (S.Kind) & " area: ");
      Put (Area (S), Fore => 1, Aft => 2, Exp => 0);
      New_Line;
   end Report;

   Wheel : constant Shape := (Kind => Circle, Radius => 1.0);
   Door  : constant Shape := (Kind => Rectangle, Width => 0.9, Height => 2.0);
   Sail  : constant Shape := (Kind => Triangle, Base => 3.0, Altitude => 4.0);

begin
   Report (Wheel);
   Report (Door);
   Report (Sail);
end Shapes;
```

Terminal

```
$ gprbuild -q shapes.adb
$ ./shapes
CIRCLE area: 3.14
RECTANGLE area: 1.80
TRIANGLE area: 6.00
```

</details>

Exercise 2.3

#### Receipts

A shop takes three kinds of payment. Every payment has an amount in cents. A card payment also records the card's last four digits, and a voucher records its six-character code. Write `receipts` with a variant record `Payment` and a procedure that prints one receipt line per payment.

Target output

```
$ ./receipts
EUR 12.50  cash
EUR 49.99  card ending 4417
EUR 5.00  voucher SPRING
```

<details>
<summary>Hint</summary>

`Amount` goes before the `case`, because every payment has one. `Last_Four : String (1 .. 4)` and `Code : String (1 .. 6)` go in their variants, and cash needs `when Cash => null;`. To print cents as euros, divide by 100 for the euros and use `rem 100` for the cents.

</details>

<details>
<summary>Solution</summary>

receipts.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Receipts is

   type Payment_Kind is (Cash, Card, Voucher);

   type Payment (Kind : Payment_Kind) is record
      Amount : Natural;   -- in cents
      case Kind is
         when Cash =>
            null;
         when Card =>
            Last_Four : String (1 .. 4);
         when Voucher =>
            Code : String (1 .. 6);
      end case;
   end record;

   function Euros (Cents : Natural) return String is
      Rest : constant String := Natural'Image (100 + Cents rem 100);
   begin
      return Natural'Image (Cents / 100) & "." & Rest (Rest'Last - 1 .. Rest'Last);
   end Euros;

   procedure Print_Line (P : Payment) is
   begin
      Put ("EUR" & Euros (P.Amount) & "  ");
      case P.Kind is
         when Cash =>
            Put_Line ("cash");
         when Card =>
            Put_Line ("card ending " & P.Last_Four);
         when Voucher =>
            Put_Line ("voucher " & P.Code);
      end case;
   end Print_Line;

begin
   Print_Line ((Kind => Cash, Amount => 1250));
   Print_Line ((Kind => Card, Amount => 4999, Last_Four => "4417"));
   Print_Line ((Kind => Voucher, Amount => 500, Code => "SPRING"));
end Receipts;
```

Terminal

```
$ gprbuild -q receipts.adb
$ ./receipts
EUR 12.50  cash
EUR 49.99  card ending 4417
EUR 5.00  voucher SPRING
```

`Euros` adds 100 to the cents before taking the image, so 5 cents becomes `105` and the last two characters are `05`, with the leading zero.

</details>

Exercise 2.4

#### Predict the crash

Read this program and decide, before running it, which line stops it and why. Then fix `Show` so it never reads a field the shape doesn't have, and the program finishes.

describe.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Describe is

   type Shape_Kind is (Circle, Rectangle);

   type Shape (Kind : Shape_Kind) is record
      case Kind is
         when Circle =>
            Radius : Float;
         when Rectangle =>
            Width, Height : Float;
      end case;
   end record;

   procedure Show (S : Shape) is
   begin
      Put_Line (Shape_Kind'Image (S.Kind));
      Put_Line ("  radius" & S.Radius'Image);
      Put_Line ("  width " & S.Width'Image);
   end Show;

begin
   Show ((Kind => Circle, Radius => 2.0));
   Show ((Kind => Rectangle, Width => 3.0, Height => 1.5));
end Describe;
```

Target output

```
$ ./describe
CIRCLE
  radius 2.00000E+00
RECTANGLE
  width  3.00000E+00
  height 1.50000E+00
```

<details>
<summary>Hint</summary>

For the circle, which of the two field reads fails? Fix it with a `case S.Kind is` that prints only the fields each kind has.

</details>

<details>
<summary>Solution</summary>

Run as written, it stops in the first call, on the line that reads `S.Width` of a circle:

Terminal

```
$ gprbuild -q describe.adb
$ ./describe
CIRCLE
  radius 2.00000E+00

raised CONSTRAINT_ERROR : describe.adb:20 discriminant check failed
```

The circle's radius printed fine; its width doesn't exist. Fixed:

describe.adb

```
with Ada.Text_IO; use Ada.Text_IO;

procedure Describe is

   type Shape_Kind is (Circle, Rectangle);

   type Shape (Kind : Shape_Kind) is record
      case Kind is
         when Circle =>
            Radius : Float;
         when Rectangle =>
            Width, Height : Float;
      end case;
   end record;

   procedure Show (S : Shape) is
   begin
      Put_Line (Shape_Kind'Image (S.Kind));
      case S.Kind is
         when Circle =>
            Put_Line ("  radius" & S.Radius'Image);
         when Rectangle =>
            Put_Line ("  width " & S.Width'Image);
            Put_Line ("  height" & S.Height'Image);
      end case;
   end Show;

begin
   Show ((Kind => Circle, Radius => 2.0));
   Show ((Kind => Rectangle, Width => 3.0, Height => 1.5));
end Describe;
```

Terminal

```
$ gprbuild -q describe.adb
$ ./describe
CIRCLE
  radius 2.00000E+00
RECTANGLE
  width  3.00000E+00
  height 1.50000E+00
```

</details>

A–Z

## Glossary

The new words in this part of Volume 2, with a link to the lesson that explains each one. Words from Volume 1 are in [its glossary](../README.md#glossary).

Append_File

The mode for opening an existing file to add lines to its end. [Lesson 1](#1)

attribute (project file)

One setting in a project file, written `for Name use value;`, like `Source_Dirs` or `Main`. [Lesson 0](#0)

child package

A package hung underneath another, named `Parent.Child` and saved as `parent-child.ads`. It can see its parent without a `with`. [Lesson 0](#0)

command-line argument

A word typed after a program's name when starting it, read with `Argument (I)`. [Lesson 1](#1)

constrained

Said of a record variable whose discriminant is fixed for good. [Lesson 2](#2)

Create

Makes a new, empty file for writing, emptying any file that already has that name. [Lesson 1](#1)

discriminant

A field in parentheses after a record type's name, set when a record is made, which the rest of the record can depend on. [Lesson 2](#2)

discriminant check

The run-time check that a record has the discriminant an operation needs; failing it raises Constraint_Error. [Lesson 2](#2)

End_Error

The exception raised by reading past the end of a file. [Lesson 1](#1)

Exec_Dir

The project attribute naming the folder the finished program goes in. [Lesson 0](#0)

exit status

The number a program hands the shell when it ends: 0 for success, anything else for failure. [Lesson 1](#1)

file handle

A `File_Type` variable: your connection to one open file. [Lesson 1](#1)

gprbuild

The tool that builds a program by following a project file. [Lesson 0](#0)

gprclean

Deletes everything gprbuild made for a project. [Lesson 0](#0)

In_File

The mode for opening a file to read it. [Lesson 1](#1)

Main

The project attribute listing the files whose procedures become programs. [Lesson 0](#0)

Name_Error

The exception raised when a file doesn't exist or its name isn't allowed. [Lesson 1](#1)

Object_Dir

The project attribute naming the folder for the compiler's leftovers. [Lesson 0](#0)

Out_File

The mode for writing a file from the beginning, used with `Create`. [Lesson 1](#1)

project file

A `.gpr` file saying where a program's sources are, where its build output goes and which switches to use. [Lesson 0](#0)

Source_Dirs

The project attribute listing the folders that hold Ada files. [Lesson 0](#0)

Standard_Error

A second output to the screen, for error messages; it isn't caught by `>`. [Lesson 1](#1)

Status_Error

The exception raised by using a file handle in the wrong state, like opening one that's already open. [Lesson 1](#1)

unconstrained

Said of a record variable whose discriminant has a default, so a whole-record assignment can change it. [Lesson 2](#2)

Use_Error

The exception raised when a file exists but can't be used that way. [Lesson 1](#1)

variant record

A record whose discriminant picks which fields it has, with a `case` inside the record. [Lesson 2](#2)

warning

A message about legal code that's probably a mistake. Unlike an error, it doesn't stop the build. [Lesson 0](#0)

Programs tested with GNAT 13.3 and gprbuild on Ubuntu 24.04, with `-gnat2022 -gnata -gnatwa`. Every terminal above was checked by running it with `verify.py`.

Your ticks are saved in this browser only.
