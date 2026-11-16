import fs from 'node:fs';
import path from 'node:path';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';

const project = path.resolve('frontend');
const config = ts.readConfigFile(path.join(project, 'tsconfig.json'), ts.sys.readFile);
const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, project);
const host = {
  getScriptFileNames: () => parsed.fileNames,
  getScriptVersion: () => '0',
  getScriptSnapshot: name => fs.existsSync(name) ? ts.ScriptSnapshot.fromString(fs.readFileSync(name, 'utf8')) : undefined,
  getCurrentDirectory: () => project,
  getCompilationSettings: () => parsed.options,
  getDefaultLibFileName: options => ts.getDefaultLibFilePath(options),
  fileExists: ts.sys.fileExists,
  readFile: ts.sys.readFile,
  readDirectory: ts.sys.readDirectory,
};
const language = ts.createLanguageService(host);
for (const fileName of parsed.fileNames) {
  const changes = language.organizeImports({ type: 'file', fileName }, {}, {});
  for (const change of changes) {
    let source = fs.readFileSync(change.fileName, 'utf8');
    for (const edit of [...change.textChanges].sort((a, b) => b.span.start - a.span.start)) {
      source = source.slice(0, edit.span.start) + edit.newText + source.slice(edit.span.start + edit.span.length);
    }
    fs.writeFileSync(change.fileName, source);
  }
}
language.dispose();
