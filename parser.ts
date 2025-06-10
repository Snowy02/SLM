import * as ts from 'typescript';
import * as fs from 'fs';
import * as path from 'path';

// --- (Interfaces remain unchanged) ---
interface ParsedNode {
    id: string; // e.g., 'File:/path/to/file.ts' or 'Component:AppComponent:/path/to/component.ts'
    type: 'File' | 'Component' | 'Service' | 'Module' | 'Pipe' | 'Directive' | 'Interface' | 'Class' | 'Unknown';
    name: string;
    filePath: string;
    properties?: Record<string, any>;
    relationships: Relationship[];
}

interface Relationship {
    type:
    | 'IMPORTS' | 'DECLARES' | 'PROVIDES' | 'IMPORTS_MODULE' | 'EXPORTS_MODULE'
    | 'BOOTSTRAPS' | 'INJECTS' | 'DEFINED_IN' | 'IMPLEMENTS' | 'USES_PIPE' | 'USES_DIRECTIVE';
    targetId: string;
    properties?: Record<string, any>;
}

interface Output {
    nodes: ParsedNode[];
}

// --- (Helper functions getDecoratorName, getDecoratorArguments, parseMetadata, resolveImportPath remain unchanged) ---
function getDecoratorName(decorator: ts.Decorator): string | undefined {
    const expression = decorator.expression;
    if (ts.isCallExpression(expression)) {
        return expression.expression.getText();
    } else if (ts.isIdentifier(expression)) {
        return expression.getText();
    }
    return undefined;
}

function getDecoratorArguments(decorator: ts.Decorator): ts.NodeArray<ts.Expression> | undefined {
    if (ts.isCallExpression(decorator.expression)) {
        return decorator.expression.arguments;
    }
    return undefined;
}

function parseMetadata(objLiteral: ts.ObjectLiteralExpression, sourceFile: ts.SourceFile): Record<string, any> {
    const metadata: Record<string, any> = {};
    objLiteral.properties.forEach(prop => {
        if (ts.isPropertyAssignment(prop) && ts.isIdentifier(prop.name)) {
            const key = prop.name.text;
            const valueNode = prop.initializer;
            if (ts.isStringLiteral(valueNode) || ts.isNumericLiteral(valueNode)) { // Check String and Numeric Literals first
                metadata[key] = valueNode.text;
            } else if (valueNode.kind === ts.SyntaxKind.TrueKeyword) { // Handle TrueKeyword
                metadata[key] = true;
            } else if (valueNode.kind === ts.SyntaxKind.FalseKeyword) { // Handle FalseKeyword
                metadata[key] = false;
            } else if (ts.isArrayLiteralExpression(valueNode)) {
                metadata[key] = valueNode.elements.map(el => el.getText(sourceFile)).filter(text => text.trim() !== '');
            } else if (ts.isIdentifier(valueNode) || ts.isPropertyAccessExpression(valueNode)) {
                metadata[key] = valueNode.getText(sourceFile);
            } else {
                metadata[key] = `[Complex Value: ${valueNode.kind}]`;
            }
        }
    });
    return metadata;
}

function resolveImportPath(importPath: string, currentFilePath: string, projectBasePath: string, tsconfigPaths?: Record<string, string[]>): string {
    if (importPath.startsWith('.')) { // Relative import
        return path.resolve(path.dirname(currentFilePath), importPath);
    }
    if (tsconfigPaths) {
        for (const [key, paths] of Object.entries(tsconfigPaths)) {
            const alias = key.replace(/\*$/, '');
            if (importPath.startsWith(alias)) {
                for (const p of paths) {
                    const resolvedPath = path.resolve(projectBasePath, p.replace(/\*$/, ''), importPath.substring(alias.length));
                    if (fs.existsSync(resolvedPath + '.ts')) return resolvedPath + '.ts';
                    if (fs.existsSync(path.join(resolvedPath, 'index.ts'))) return path.join(resolvedPath, 'index.ts');
                    if (fs.existsSync(resolvedPath)) return resolvedPath;
                }
            }
        }
    }
    const possibleLocalPath = path.resolve(projectBasePath, importPath + '.ts');
    if (fs.existsSync(possibleLocalPath)) {
        return possibleLocalPath;
    }
    return importPath;
}

/**
 * NEW: Recursively finds all tsconfig.json/tsconfig.app.json files in a directory.
 */
function findTsConfigs(dir: string, ignore: string[] = ['node_modules', '.git', 'dist']): string[] {
    let configs: string[] = [];
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory() && !ignore.includes(entry.name)) {
            configs = configs.concat(findTsConfigs(fullPath, ignore));
        } else if (entry.isFile() && (entry.name === 'tsconfig.json' || entry.name === 'tsconfig.app.json')) {
            // We only care about configs that actually include files to compile
            try {
                const content = fs.readFileSync(fullPath, 'utf8');
                const json = JSON.parse(content);
                if (json.files || json.include) {
                    configs.push(fullPath);
                }
            } catch (e) {
                console.error(`Could not read or parse ${fullPath}. Skipping.`);
            }
        }
    }
    return configs;
}

/**
 * REFACTORED: Parses a single TypeScript project defined by a tsconfig file
 * and adds its nodes to the shared collections.
 */
function parseProjectFromTsConfig(
    tsconfigPath: string,
    monorepoRoot: string,
    allNodes: ParsedNode[],
    fileMap: Map<string, ParsedNode>
) {
    console.error(`--- Parsing project from: ${path.relative(monorepoRoot, tsconfigPath)} ---`);

    const configFile = ts.readConfigFile(tsconfigPath, ts.sys.readFile);
    const compilerOptions = ts.parseJsonConfigFileContent(
        configFile.config,
        ts.sys,
        path.dirname(tsconfigPath) // Use the tsconfig's directory as the base
    );

    const program = ts.createProgram(compilerOptions.fileNames, compilerOptions.options);
    const normalizedMonorepoRoot = path.normalize(monorepoRoot).toLowerCase();

    for (const sourceFile of program.getSourceFiles()) {
        const normalizedSourcePath = path.normalize(sourceFile.fileName).toLowerCase();
        if (sourceFile.isDeclarationFile || !normalizedSourcePath.startsWith(normalizedMonorepoRoot)) {
            continue;
        }

        // Use path relative to monorepo root for consistent IDs
        const relativeFilePath = path.relative(monorepoRoot, sourceFile.fileName).replace(/\\/g, '/');
        const fileId = `File:${relativeFilePath}`;

        if (!fileMap.has(fileId)) {
            const fileNode: ParsedNode = {
                id: fileId,
                type: 'File',
                name: path.basename(sourceFile.fileName),
                filePath: relativeFilePath,
                relationships: [],
            };
            allNodes.push(fileNode);
            fileMap.set(fileId, fileNode);
        }
        const currentFileNode = fileMap.get(fileId)!;

        ts.forEachChild(sourceFile, (node) => {
            if (ts.isImportDeclaration(node) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) {
                const importPathRaw = node.moduleSpecifier.text;
                // Use monorepoRoot as the base for resolving aliases
                const resolvedImportPath = resolveImportPath(importPathRaw, sourceFile.fileName, monorepoRoot, compilerOptions.options.paths);
                const targetRelativePath = path.relative(monorepoRoot, resolvedImportPath).replace(/\\/g, '/');
                const targetFileId = `File:${targetRelativePath}`;

                if (fileMap.has(targetFileId) || !resolvedImportPath.startsWith('.')) {
                    currentFileNode.relationships.push({
                        type: 'IMPORTS',
                        targetId: fileMap.has(targetFileId) ? targetFileId : `External:${importPathRaw}`,
                        properties: { from: importPathRaw }
                    });
                }
            } else if (ts.isClassDeclaration(node) && node.name) {
                const className = node.name.text;
                let entityType: ParsedNode['type'] = 'Class';
                // ID is always Type:Name:Path-from-monorepo-root
                let entityId = `Class:${className}:${relativeFilePath}`;
                let entityProperties: Record<string, any> = {};
                const entityRelationships: Relationship[] = [];

                const decorators = ts.getDecorators(node);
                if (decorators) {
                    for (const decorator of decorators) {
                        const decoratorName = getDecoratorName(decorator);
                        const decoratorArgs = getDecoratorArguments(decorator);

                        if (decoratorName === 'Component') {
                            entityType = 'Component';
                            entityId = `Component:${className}:${relativeFilePath}`;
                            if(decoratorArgs && decoratorArgs[0] && ts.isObjectLiteralExpression(decoratorArgs[0])) {
                                 const metadata = parseMetadata(decoratorArgs[0], sourceFile);
                                 if (metadata.selector) entityProperties['selector'] = metadata.selector;
                                 if (metadata.templateUrl) entityProperties['templateUrl'] = metadata.templateUrl;
                                 if (metadata.styleUrls) entityProperties['styleUrls'] = metadata.styleUrls;
                            }
                        } else if (decoratorName === 'Injectable') {
                            entityType = 'Service';
                            entityId = `Service:${className}:${relativeFilePath}`;
                            if(decoratorArgs && decoratorArgs[0] && ts.isObjectLiteralExpression(decoratorArgs[0])) {
                                 const metadata = parseMetadata(decoratorArgs[0], sourceFile);
                                 if (metadata.providedIn) entityProperties['providedIn'] = metadata.providedIn;
                            }
                        } else if (decoratorName === 'NgModule' && decoratorArgs && decoratorArgs[0] && ts.isObjectLiteralExpression(decoratorArgs[0])) {
                           entityType = 'Module';
                           entityId = `Module:${className}:${relativeFilePath}`;
                           const metadata = parseMetadata(decoratorArgs[0], sourceFile);
                           (metadata.declarations || []).forEach((name: string) => entityRelationships.push({ type: 'DECLARES', targetId: `Unknown:${name}:${relativeFilePath}` }));
                           (metadata.imports || []).forEach((name: string) => entityRelationships.push({ type: 'IMPORTS_MODULE', targetId: `Module:${name}:UNKNOWN_PATH` }));
                           (metadata.providers || []).forEach((name: string) => entityRelationships.push({ type: 'PROVIDES', targetId: `Service:${name}:UNKNOWN_PATH` }));
                           (metadata.exports || []).forEach((name: string) => entityRelationships.push({ type: 'EXPORTS_MODULE', targetId: `UnknownExport:${name}:UNKNOWN_PATH` }));
                           (metadata.bootstrap || []).forEach((name: string) => entityRelationships.push({ type: 'BOOTSTRAPS', targetId: `Component:${name}:UNKNOWN_PATH` }));
                        }
                        // Add other decorator handlers (Pipe, Directive) here...
                    }
                }
                
                // Constructor Injection
                if(node.members) {
                    for(const member of node.members) {
                        if (ts.isConstructorDeclaration(member) && member.parameters) {
                            member.parameters.forEach(param => {
                                if (param.type && param.name && ts.isIdentifier(param.name)) {
                                    const paramTypeName = param.type.getText(sourceFile);
                                    entityRelationships.push({ type: 'INJECTS', targetId: `Service:${paramTypeName}:UNKNOWN_PATH`, properties: { parameterName: param.name.text }});
                                }
                            });
                        }
                    }
                }

                // Implements clauses
                if(node.heritageClauses) {
                    node.heritageClauses.forEach(clause => {
                        if (clause.token === ts.SyntaxKind.ImplementsKeyword) {
                            clause.types.forEach(type => {
                                const interfaceName = type.expression.getText(sourceFile);
                                entityRelationships.push({ type: 'IMPLEMENTS', targetId: `Interface:${interfaceName}:UNKNOWN_PATH` });
                            });
                        }
                    });
                }
                
                const existingNode = allNodes.find(n => n.id === entityId);
                if (existingNode) {
                    existingNode.type = entityType;
                    existingNode.properties = { ...existingNode.properties, ...entityProperties };
                    existingNode.relationships.push(...entityRelationships);
                } else {
                    allNodes.push({ id: entityId, type: entityType, name: className, filePath: relativeFilePath, properties: entityProperties, relationships: entityRelationships });
                }

            } else if (ts.isInterfaceDeclaration(node) && node.name) {
                const interfaceName = node.name.text;
                const interfaceId = `Interface:${interfaceName}:${relativeFilePath}`;
                if (!fileMap.has(interfaceId)) {
                     allNodes.push({ id: interfaceId, type: 'Interface', name: interfaceName, filePath: relativeFilePath, relationships: [] });
                }
            }
        });
    }
}

/**
 * NEW: The main orchestrator for monorepo parsing.
 */
function parseMonorepo(rootPath: string): Output {
    const allNodes: ParsedNode[] = [];
    const fileMap = new Map<string, ParsedNode>(); // Global map for all nodes

    const tsconfigFiles = findTsConfigs(rootPath);
    if (tsconfigFiles.length === 0) {
        console.error("Warning: No 'tsconfig.json' or 'tsconfig.app.json' files found with 'files' or 'include' properties.");
        return { nodes: [] };
    }

    // 1. Parse all projects and aggregate nodes
    for (const tsconfigPath of tsconfigFiles) {
        try {
            parseProjectFromTsConfig(tsconfigPath, rootPath, allNodes, fileMap);
        } catch(e: any) {
            console.error(`\nERROR parsing project from ${tsconfigPath}. Skipping. \nDetails: ${e.message}\n`);
        }
    }

    // 2. Resolve relationships globally now that all nodes are known
    for (const node of allNodes) {
        for (const rel of node.relationships) {
            if (rel.targetId.endsWith(':UNKNOWN_PATH') || rel.targetId.startsWith('Unknown:') || rel.targetId.startsWith('UnknownExport:')) {
                const parts = rel.targetId.split(':');
                const targetTypeHint = parts[0];
                const targetName = parts[1];

                // Find a matching node by name across the entire monorepo
                const potentialTargets = allNodes.filter(n =>
                    n.name === targetName &&
                    (targetTypeHint.startsWith('Unknown') || n.id.startsWith(`${targetTypeHint}:`))
                );

                if (potentialTargets.length === 1) {
                    rel.targetId = potentialTargets[0].id;
                } else if (potentialTargets.length > 1) {
                    console.warn(`Ambiguous relationship: ${node.id} -> ${rel.targetId}. Found ${potentialTargets.length} candidates.`);
                    rel.targetId = `Ambiguous:${targetName}`;
                } else {
                    rel.targetId = `Unresolved:${targetName}`;
                }
            }
        }
    }

    return { nodes: allNodes };
}


// --- Main Execution ---
if (require.main === module) {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.error("Usage: node parser.js <pathToMonorepoProjectRoot>");
        process.exit(1);
    }
    const projectPath = path.resolve(args[0]);
    if (!fs.existsSync(projectPath)) {
        console.error(`Project path does not exist: ${projectPath}`);
        process.exit(1);
    }

    const parsedData = parseMonorepo(projectPath);
    console.log(JSON.stringify(parsedData, null, 2));
}
