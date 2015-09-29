Building autotag
================

Autotag uses node and webpack.

Note: npm issue
===============
Currently a dependancy of autotag has a npm package resolution conflict
which leads to a runtime error as `React` must be a monolith.

This can currently be addressed after `npm install` by removing the `React`
dependancy of the module in question:

``` bash
rm -r node_modules/react-range/node_modules/react
```

Building for production
=======================

This will build `static/autotag/js/bundle.js` which contains basically the whole
project including CSS. It is minified.

``` bash
cd autotag
npm install
node_modules/webpack/bin/webpack.js -p
```

Building for development
========================

This will detect changes and rebuild `static/autotag/js/bundle.js` when there
are any. This works in conjunction with django development server as that
will be monitoring `bundle.js` for any changes.

``` bash
cd autotag
npm install
node_modules/webpack/bin/webpack.js --watch
```
