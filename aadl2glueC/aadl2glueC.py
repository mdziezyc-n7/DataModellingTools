#!/usr/bin/env python
# vim: set expandtab ts=8 sts=4 shiftwidth=4
#
# (C) Semantix Information Technologies.
#
# Semantix Information Technologies is licensing the code of the
# Data Modelling Tools (DMT) in the following dual-license mode:
#
# Commercial Developer License:
#       The DMT Commercial Developer License is the suggested version
# to use for the development of proprietary and/or commercial software.
# This version is for developers/companies who do not want to comply
# with the terms of the GNU Lesser General Public License version 2.1.
#
# GNU LGPL v. 2.1:
#       This version of DMT is the one to use for the development of
# applications, when you are willing to comply with the terms of the
# GNU Lesser General Public License version 2.1.
#
# Note that in both cases, there are no charges (royalties) for the
# generated code.
#
'''
Code Integrator

This is the core of the "glue" generators that Semantix developed for
the European research project ASSERT. It has been enhanced in the
context of Data Modelling and Data Modelling Tuning projects,
and continuous to evolve over the course of other projects.

This code starts by reading the AADL specification of the system.
It then generates the runtime bridge-code that will map the message
data structures from those generated by the Semantix Certified ASN.1
compiler to/from those generated by the modeling tool used to
functionally model the APLC subsystem (e.g. SCADE, ObjectGeode,
Matlab/Simulink, C, Ada, etc).

The code generation is done via user-visible (and editable) backends.

There are three kinds of backends:

1. Synchronous backends
=======================

For these, the working logic is:

for each subprogram implementation
    Load B mapper
    call OnStartup
    for each subprogram param
        Call OnBasic/OnSequence/OnEnumerated etc
    call OnShutdown

That is, there is OnStartup/OnInteger/OnSequence/.../OnShutdown cycle
done PER EACH SUBPROGRAM.

2. Asynchronous backends
========================

Asynchronous backends are only generating standalone encoders and decoders
(they are not doing this per sp.param).

The working logic is therefore different

OnStartup called ONCE for each async backend in use (used by this system's PIs)
Via the asynchronous.py, after visiting all params and collecting them,
for each asn.1 type that is actually used (at least once) as a param:
    Call Encoder and Decoder
Call OnShutdown ONCE for each async backend in use (used by this system's PIs)

3. Special backends
===================

GUI, Python, (VHDL?), etc...

These have custom requirements, so each one is handled by specific AADL2GLUEC
code. As it is now, the pattern follows that of the synchronous backends,
but with an extra call to OnFinal at the end.
'''

import os
import sys
import copy
import distutils.spawn as spawn
from importlib import import_module

import commonPy.configMT

import commonPy.asnParser
import commonPy.aadlAST
import commonPy.cleanupNodes

#import aadlParser
import AadlLexer
import AadlParser

import antlr

from commonPy.utility import panic, warn, inform

import commonPy.verify as verify

g_mappedName = {
    'SEQUENCE': 'OnSequence',
    'SET': 'OnSet',
    'CHOICE': 'OnChoice',
    'SEQUENCEOF': 'OnSequenceOf',
    'SETOF': 'OnSetOf',
    'ENUMERATED': 'OnEnumerated'
}


# def CreateInitializationFiles(useOSS, unused_SystemsAndImplementations, asnFiles):
#     '''This function is called once at the beginning of the
# code generation process.'''
#
# Obsolete: No more support for OSS (ESA, 2009/Dec/04)
#
#    initializationFile = open(commonPy.configMT.outputDir + 'Initialization.c', 'w')
#
#    OssDefinition =""
#    OssInit = ""
#    OssInclude = ""
#    if useOSS:
#       OssDefinition = "OssGlobal w, *g_world = &w;"
#       if len(asnFiles):
#           asnFile = asnFiles[0]
#           asnName = os.path.basename( os.path.splitext(asnFile)[0] )
#           OssInit = "ossinit(g_world, %s);" % asnName
#           OssInclude = "#include <ossasn1.h>\n#include \"%s.oss.h\"" % asnName
#       else:  # pragma: no cover
#           OssInclude = "#include <ossasn1.h>\n"  # pragma: no cover
#    initializationFile.write('''
#/* This file contains the initialization code for the "glue".
#   InitializeGlue() must be called before calling any of the "glue" functions.
#   It sets up the appropriately sized private heap for the encoding/decoding
#   of the messages. */
#
#%(OssInclude)s
#
#%(OssDefinition)s
#
#void InitializeGlue()
#{
#    static int initialized = 0;
#
#    if (!initialized) {
#       initialized = 1;
#       %(OssInit)s
#    }
#}
#''' % {"OssDefinition":OssDefinition, "OssInit":OssInit, "OssInclude":OssInclude})
#
#    initializationFile.close()
#    initializationAdaFile = open(commonPy.configMT.outputDir + 'initializevmglue.adb', 'w')
#    initializationAdaFile.write('''
#package body InitializeVMGlue is
#
#procedure InitializeGlueMemory is
#    procedure C_InitializeGlueMemory;
#    pragma Import(C, C_InitializeGlueMemory, "InitializeGlue");
#begin
#    C_InitializeGlueMemory;
#end InitializeGlueMemory;
#
#end InitializeVMGlue;
#''')
#    initializationAdaFile.close()
#    initializationAdaHeader = open(commonPy.configMT.outputDir + 'initializevmglue.ads', 'w')
#    initializationAdaHeader.write('''
#package InitializeVMGlue is
#
#procedure InitializeGlueMemory;
#
#end InitializeVMGlue;
#''')
#    initializationAdaHeader.close()


def ParseAADLfilesAndResolveSignals():
    '''Invokes the ANTLR generated AADL parser, and resolves
all references to AAADL Data types into the param._signal member
of each SUBPROGRAM param.'''
    for aadlFilename in sys.argv[1:]:
        # Parse AADL system description files
        inform("Parsing %s...", aadlFilename)
        #aadlParser.ParseInput("\n".join(open(aadlFilename,'r').readlines()))

        L = AadlLexer.Lexer(aadlFilename)
        P = AadlParser.Parser(L)
        L.setFilename(aadlFilename)
        P.setFilename(L.getFilename())
        try:
            P.aadl_specification()
        except antlr.ANTLRException, e:  # pragma: no cover
            panic("Error in file '%s': %s\n" % (e.fileName, str(e)))  # pragma: no cover

    # Resolve signal definitions over all input AADL files
    for subProgramName, subProgram in commonPy.aadlAST.g_apLevelContainers.iteritems():
        inform("Resolving data definitions in subprogram %s..." % subProgramName)
        for param in subProgram._params:
            if not isinstance(param._signal, commonPy.aadlAST.Signal):
                if param._signal not in commonPy.aadlAST.g_signals:
                    panic("Unknown data type %s in the definition of %s!\n" %  # pragma: no cover
                          (param._signal, subProgramName))  # pragma: no cover
                param._signal = commonPy.aadlAST.g_signals[param._signal]


def SpecialCodes(unused_SystemsAndImplementations, unused_uniqueDataFiles, asnFiles, unused_useOSS):
    '''This function handles the code generations needs that reside outside
the scope of individual parameters (e.g. it needs access to all ASN.1
types). This used to cover Dumpable C/Ada Types and OG headers.'''
    outputDir = commonPy.configMT.outputDir
    asn1SccPath = spawn.find_executable('asn1.exe')
    if len(asnFiles) != 0:
        if not asn1SccPath:
            panic("ASN1SCC seems not installed on your system (asn1.exe not found in PATH).\n")  # pragma: no cover
        #os.system("mono \"{asn$ASN1SCC\" -wordSize 8 -typePrefix asn1Scc -Ada -equal -uPER -o \"" + outputDir + "\" \"" + "\" \"".join(asnFiles) + "\"")
        os.system('mono "{}" -wordSize 8 -typePrefix asn1Scc -Ada -equal -uPER -o "{}" "{}"'
                  .format(asn1SccPath,
                          outputDir,
                          '" "'.join(asnFiles)))


def main():
    sys.path.append(os.path.abspath(os.path.dirname(sys.argv[0])))
    if sys.argv.count("-o") != 0:
        idx = sys.argv.index("-o")
        try:
            commonPy.configMT.outputDir = os.path.normpath(sys.argv[idx+1]) + os.sep
        except:  # pragma: no cover
            panic('Usage: %s [-verbose] [-useOSS] [-o dirname] input1.aadl [input2.aadl] ...\n' % sys.argv[0])  # pragma: no cover
        del sys.argv[idx]
        del sys.argv[idx]
        if not os.path.isdir(commonPy.configMT.outputDir):
            panic("'%s' is not a directory!\n" % commonPy.configMT.outputDir)  # pragma: no cover
#    if "-lexonly" in sys.argv:
#       commonPy.configMT.debugParser = True
#       sys.argv.remove("-lexonly")
    if "-onlySP" in sys.argv:  # pragma: no cover
        commonPy.configMT.g_bOnlySubprograms = True  # pragma: no cover
        sys.argv.remove("-onlySP")  # pragma: no cover
    if "-verbose" in sys.argv:
        commonPy.configMT.verbose = True
        sys.argv.remove("-verbose")
#    if "-ignoreINTEGERranges" in sys.argv:
#       commonPy.configMT.args.append("-ignoreINTEGERranges")
#       sys.argv.remove("-ignoreINTEGERranges")
#    if "-ignoreREALranges" in sys.argv:
#       commonPy.configMT.args.append("-ignoreREALranges")
#       sys.argv.remove("-ignoreREALranges")
    useOSS = "-useOSS" in sys.argv
    if useOSS:
        sys.argv.remove("-useOSS")

    # No other options must remain in the cmd line...
    if len(sys.argv) < 2:
        panic('Usage: %s [-verbose] [-useOSS] [-o dirname] input1.aadl [input2.aadl] ...\n' % sys.argv[0])  # pragma: no cover
    commonPy.configMT.showCode = True
    for f in sys.argv[1:]:
        if not os.path.isfile(f):
            panic("'%s' is not a file!\n" % f)  # pragma: no cover

    ParseAADLfilesAndResolveSignals()

    uniqueDataFiles = {}
    for sp in commonPy.aadlAST.g_apLevelContainers.values():
        for param in sp._params:
            uniqueDataFiles.setdefault(param._signal._asnFilename, {})
            uniqueDataFiles[param._signal._asnFilename].setdefault(sp._language, [])
            uniqueDataFiles[param._signal._asnFilename][sp._language].append(sp)

    uniqueASNfiles = {}
#    for asnFile in uniqueDataFiles.iterkeys():
#       commonPy.asnParser.ParseInput(asnFile)
#       uniqueASNfiles[asnFile] = [copy.copy(commonPy.asnParser.g_names),copy.copy(commonPy.asnParser.g_inputAsnAST),copy.copy(commonPy.asnParser.g_leafTypeDict)]
#    if 0 == len(uniqueDataFiles.iterkeys()):
#       panic("There are no data references anywhere in the given AADL files. Aborting...")
#       sys.exit(0)

    if len(uniqueDataFiles.keys()) != 0:
        commonPy.asnParser.ParseAsnFileList(uniqueDataFiles.keys())

    for asnFile in uniqueDataFiles:
        tmpNames = {}
        for name in commonPy.asnParser.g_typesOfFile[asnFile]:
            tmpNames[name] = commonPy.asnParser.g_names[name]

        uniqueASNfiles[asnFile] = [
            copy.copy(tmpNames),                            # map Typename to type definition class from asnAST
            copy.copy(commonPy.asnParser.g_astOfFile[asnFile]),    # list of nameless type definitions
            copy.copy(commonPy.asnParser.g_leafTypeDict)]   # map from Typename to leafType

        inform("Checking that all base nodes have mandatory ranges set in %s..." % asnFile)
        for node in tmpNames.values():
            verify.VerifyRanges(node, commonPy.asnParser.g_names)

#    # For each ASN.1 grammar file referenced in the system level description
#    for asnFile in uniqueDataFiles.iterkeys():
#       names = uniqueASNfiles[asnFile][0]
#       leafTypeDict = uniqueASNfiles[asnFile][2]
#
#       modelingLanguages = uniqueDataFiles[asnFile]
#
#       # For each modeling language used by subprograms whose messages reference the grammar
#       for modelingLanguage, subProgramArray in modelingLanguages.iteritems():
#           if modelingLanguage == None:
#               continue
#
#           for sp in subProgramArray:

    loadedBackends = {}

    SystemsAndImplementations = commonPy.aadlAST.g_subProgramImplementations[:]
    SystemsAndImplementations.extend(commonPy.aadlAST.g_threadImplementations[:])
    SystemsAndImplementations.extend(commonPy.aadlAST.g_processImplementations[:])

    # obsolete, was used for OSS library init
    # CreateInitializationFiles(useOSS, SystemsAndImplementations, uniqueDataFiles.iterkeys())

    # Update ASN.1 nodes to carry size info (only for Signal params)
    for si in SystemsAndImplementations:
        sp, sp_impl, modelingLanguage = si[0], si[1], si[2]
        sp = commonPy.aadlAST.g_apLevelContainers[sp]
        for param in sp._params:
            asnFile = param._signal._asnFilename
            names = uniqueASNfiles[asnFile][0]
            leafTypeDict = uniqueASNfiles[asnFile][2]
            for nodeTypename in names:
                if nodeTypename != param._signal._asnNodename:
                    continue
                node = names[nodeTypename]
                if node._leafType == "AsciiString":
                    panic("You cannot use IA5String as a parameter - use OCTET STRING instead\n(%s)" % node.Location())  # pragma: no cover
                node._asnSize = param._signal._asnSize

    # If some AST nodes must be skipped (for any reason), go learn about them
    commonPy.cleanupNodes.DiscoverBadTypes()

    if {"ada", "qgenada"} & {y[2].lower() for y in SystemsAndImplementations}:
        SpecialCodes(SystemsAndImplementations, uniqueDataFiles, uniqueASNfiles, useOSS)

    asynchronousBackends = []

    for si in SystemsAndImplementations:
        sp, sp_impl, modelingLanguage, maybeFVname = si[0], si[1], si[2], si[3]
        sp = commonPy.aadlAST.g_apLevelContainers[sp]
        inform("Creating glue for parameters of %s.%s...", sp._id, sp_impl)
        if modelingLanguage is None:
            continue  # pragma: no cover

        # Avoid generating empty glue - no parameters for this APLC
        if len(sp._params) == 0:
            continue

        # All SCADE versions are handled by lustre_B_mapper
        # if modelingLanguage[:6] == "Lustre" or modelingLanguage[:5] == "SCADE":
        #    modelingLanguage = "Lustre"  # pragma: no cover

        # The code for these mappers needs C ASN.1 codecs
        if modelingLanguage.lower() in ["gui_ri", "gui_pi", "vhdl", "rhapsody"]:
            modelingLanguage = "C"

        backendFilename = "." + modelingLanguage.lower() + "_B_mapper.py"
        inform("Parsing %s...", backendFilename)
        try:
            backend = import_module(backendFilename[:-3], 'aadl2glueC')
            if backendFilename[:-3] not in loadedBackends:
                loadedBackends[backendFilename[:-3]] = 1
                if commonPy.configMT.verbose:
                    backend.Version()
        except ImportError as err:  # pragma: no cover
            panic("Failed to load backend ({}) for {}.{}: {}\n".format(backendFilename, sp._id, sp_impl, str(err)))  # pragma: no cover
            continue  # pragma: no cover

        # Asynchronous backends are only generating standalone encoders and decoders
        # (they are not doing this per sp.param).
        #
        # They must however do this when they have collected ALL the types they are
        # supposed to handle, so this can only be done when the loop over
        # SystemsAndImplementations has completed. We therefore accumulate them in a
        # container, and call their 'OnShutdown' method (which generates the encoders
        # and decoders) at the end (outside the loop). This of course means that we
        # can only call OnStartup once (when the backend is first loaded)
        if backend.isAsynchronous:
            if backend not in asynchronousBackends:
                asynchronousBackends.append(backend)
                # Only call OnStartup ONCE for asynchronous backends
                if 'OnStartup' in dir(backend):
                    # Also notice, no SP or SPIMPL are passed. We are asynchronous, so
                    # we only generate "generic" encoders and decoders, not SP-specific ones.
                    backend.OnStartup(modelingLanguage, asnFile, commonPy.configMT.outputDir, maybeFVname, useOSS)
        else:
            # In synchronous tools, always call OnStartup and OnShutdown for each SystemsAndImplementation
            if 'OnStartup' in dir(backend):
                backend.OnStartup(modelingLanguage, asnFile, sp, sp_impl, commonPy.configMT.outputDir, maybeFVname, useOSS)

        for param in sp._params:
            inform("Creating glue for param %s...", param._id)
            asnFile = param._signal._asnFilename
            #names = uniqueASNfiles[asnFile][0]
            names = commonPy.asnParser.g_names
            #leafTypeDict = uniqueASNfiles[asnFile][2]
            leafTypeDict = commonPy.asnParser.g_leafTypeDict

            inform("This param uses definitions from %s", asnFile)
            for nodeTypename in names:
                # Check if this type must be skipped
                if commonPy.cleanupNodes.IsBadType(nodeTypename):
                    continue

                # Async backends need to collect all types and create Encode/Decode functions for them.
                # So we allow async backends to pass thru this "if" - the collection of types
                # is done in the typesToWorkOn dictionary *inside* the base class (asynchronousTool.py)
                if (not backend.isAsynchronous) and nodeTypename != param._signal._asnNodename:
                    # For sync tools, only allow the typename we are using in this param to pass
                    continue
                node = names[nodeTypename]
                inform("ASN.1 node is %s", nodeTypename)

                # First, make sure we know what leaf type this node is
                if node._isArtificial:
                    continue  # artificially created (inner) type

                leafType = leafTypeDict[nodeTypename]
                # If it is a base type,
                if leafType in ['BOOLEAN', 'INTEGER', 'REAL', 'OCTET STRING']:
                    # make sure we have mapping instructions for BASE elements
                    if 'OnBasic' not in dir(backend):
                        panic("ASN.1 grammar contains literal(%s) but no BASE section found in the mapping grammar (%s)" % (nodeTypename, backendFilename))  # pragma: no cover
                    if not backend.isAsynchronous:
                        backend.OnBasic(nodeTypename, node, sp, sp_impl, param, leafTypeDict, names)
                    else:
                        backend.OnBasic(nodeTypename, node, leafTypeDict, names)
                # if it is a complex type
                elif leafType in ['SEQUENCE', 'SET', 'CHOICE', 'SEQUENCEOF', 'SETOF', 'ENUMERATED']:
                    # make sure we have mapping instructions for the element
                    if g_mappedName[leafType] not in dir(backend):
                        panic("ASN.1 grammar contains %s but no %s section found in the mapping grammar (%s)" % (nodeTypename, g_mappedName[leafType], backendFilename))  # pragma: no cover
                    processor = backend.__dict__[g_mappedName[leafType]]
                    if not backend.isAsynchronous:
                        processor(nodeTypename, node, sp, sp_impl, param, leafTypeDict, names)
                    else:
                        processor(nodeTypename, node, leafTypeDict, names)
                # what type is it?
                else:  # pragma: no cover
                    panic("Unexpected type of element: %s" % leafTypeDict[nodeTypename])  # pragma: no cover

        # For synchronous backend, call OnShutdown once per each sp_impl
        if not backend.isAsynchronous:
            if 'OnShutdown' in dir(backend):
                backend.OnShutdown(modelingLanguage, asnFile, sp, sp_impl, maybeFVname)

    # SystemsAndImplementation loop completed - time to call OnShutdown ONCE for each async backend that we loaded
    for asyncBackend in asynchronousBackends:
        if 'OnShutdown' in dir(backend):
            asyncBackend.OnShutdown(modelingLanguage, asnFile, maybeFVname)

    # The code generators for GUIs, Python mappers and VHDL mappers are different: they need access to
    # both ASN.1 types and SP params.
    # Custom code follows...

    # Do we need to handle any special subprograms?
    workedOnGUIs = False
    workedOnVHDL = False

    def mappers(lang):
        if lang.lower() in ["gui_pi", "gui_ri"]:
            return [import_module(".python_B_mapper", "aadl2glueC"),
                    import_module(".pyside_B_mapper", "aadl2glueC")]
        elif lang.lower() == "vhdl":  # pragma: no cover
            return [import_module(".vhdl_B_mapper", "aadl2glueC")]  # pragma: no cover

    for si in [x for x in SystemsAndImplementations if x[2] is not None and x[2].lower() in ["gui_ri", "gui_pi", "vhdl"]]:
        # We do, start the work
        sp, sp_impl, lang, maybeFVname = si[0], si[1], si[2], si[3]
        sp = commonPy.aadlAST.g_apLevelContainers[sp]
        if len(sp._params) == 0:
            if lang.lower() == "gui_ri":  # pragma: no cover
                if "gui_polling" not in sp._id:  # pragma: no cover
                    panic("Due to wxWidgets limitations, your TCs must have at least one parameter (fix %s)" % sp._id)  # pragma: no cover
            continue  # pragma: no cover
        if lang.lower() in ["gui_pi", "gui_ri"]:
            workedOnGUIs = True
        if lang.lower() == "vhdl":
            workedOnVHDL = True  # pragma: no cover
        inform("Creating %s for %s.%s", lang.upper(), sp._id, sp_impl)
        for b in mappers(lang):
            b.OnStartup(lang, asnFile, sp, sp_impl, commonPy.configMT.outputDir, maybeFVname, useOSS)
        for param in sp._params:
            inform("Processing param %s...", param._id)
            asnFile = param._signal._asnFilename
            names = commonPy.asnParser.g_names
            leafTypeDict = commonPy.asnParser.g_leafTypeDict
            nodeTypename = param._signal._asnNodename
            node = names[nodeTypename]
            inform("ASN.1 node is %s", nodeTypename)
            #if node._isArtificial:
            #    continue # artificially created (inner) type pragma: no cover
            leafType = leafTypeDict[nodeTypename]
            if leafType in ['BOOLEAN', 'INTEGER', 'REAL', 'OCTET STRING']:
                for b in mappers(lang):
                    b.OnBasic(nodeTypename, node, sp, sp_impl, param, leafTypeDict, names)
            elif leafType in ['SEQUENCE', 'SET', 'CHOICE', 'SEQUENCEOF', 'SETOF', 'ENUMERATED']:
                for b in mappers(lang):
                    processor = b.__dict__[g_mappedName[leafType]]
                    processor(nodeTypename, node, sp, sp_impl, param, leafTypeDict, names)
            else:  # pragma: no cover
                panic("Unexpected type of element: %s" % leafTypeDict[nodeTypename])  # pragma: no cover
        for b in mappers(lang):
            b.OnShutdown(lang, asnFile, sp, sp_impl, maybeFVname)
    # if we processed any GUI subprogram, add footers and close files
    if workedOnGUIs:
        for b in mappers('gui_ri'):
            b.OnFinal()
    # if we processed any VHDL subprogram, add footers and close files
    if workedOnVHDL:
        for b in mappers('vhdl'):  # pragma: no cover
            b.OnFinal()  # pragma: no cover

if __name__ == "__main__":
    if "-pdb" in sys.argv:
        sys.argv.remove("-pdb")  # pragma: no cover
        import pdb  # pragma: no cover
        pdb.run('main()')  # pragma: no cover
    else:
        main()
