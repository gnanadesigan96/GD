import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import replace from '@rollup/plugin-replace';
import terser from '@rollup/plugin-terser';

export default {
  input: 'src/index.js',
  output: [
    {
      file: 'dist/sdk.js',
      format: 'iife',
      name: 'SessionReplay',
      sourcemap: true,
    },
    {
      file: 'dist/sdk.min.js',
      format: 'iife',
      name: 'SessionReplay',
      plugins: [terser()],
    },
  ],
  plugins: [
    replace({
      'process.env.NODE_ENV': JSON.stringify('production'),
      preventAssignment: true,
    }),
    resolve({ browser: true }),
    commonjs(),
  ],
};
