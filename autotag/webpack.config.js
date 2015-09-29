// webpack.config.js

var path = require('path');

module.exports = {
  entry: './src/main.jsx',
  output: {
    path: './static/autotag/js',
    filename: 'bundle.js',
    library: 'autotagform'
  },
  module: {
    loaders: [
      {
        test: /\.jsx$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
        query: {
          presets: ['react', 'es2015']
        }
      },
      {
        test: /\.css$/, // Only .css files
        loader: 'style-loader!css-loader' // Run both loaders
      },
      { test: /\.png$/,
        loader: "url-loader?limit=100000"
      }
    ]
  },
  resolve: {
    extensions: ['', '.js', '.jsx', '.json']
  },
};
