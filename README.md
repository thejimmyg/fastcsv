# FastCSV

A Python library (with c implementation on the way) for creating padded CSV files with sorted rows that can be quickly read.

## License

[GNU AGPL3](http://www.gnu.org/licenses/agpl-3.0.html).

## Compiling the C extension
 
~~~
sudo apt-get install build-essential
gcc -Wall -c -fPIC fastcsv.c -o fastcsv.o
gcc -shared -Wl,-soname,libfastcsv.so.0 -o libfastcsv.so.0.0.1 fastcsv.o
~~~

## Usage

This library is used in [CSVBlog](https://github.com/thejimmyg/csvblog). Have a look there for usage information.
