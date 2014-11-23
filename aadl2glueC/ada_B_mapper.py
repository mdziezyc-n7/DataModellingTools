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
This is the implementation of the code mapper for Ada code.
As initially envisioned, ASSERT technology is not supposed
to support manually-made systems. A migration path, however,
that allows legacy hand-written code and modelling-tool
generated code to co-exist, can be beneficial in allowing
for a smooth transition. To that end, this backend (as well as
the C one) are written.

This is a backend for Semantix's code generator B (aadl2glueC).

Ada is a member of the asynchronous "club" (SDL, etc);
The subsystem developer (or rather, the APLC developer) is using
native Ada code to work with code generated by modelling tools.
To that end, this backend creates "glue" functions for input and
output parameters, which have Ada callable interfaces.
'''

# from commonPy.utility import panic
# from recursiveMapper import RecursiveMapper
# from asynchronousTool import ASynchronousToolGlueGenerator

import c_B_mapper

isAsynchronous = True
adaBackend = None
cBackend = None


def Version():
    print "Code generator: " + "$Id: ada_B_mapper.py 2382 2012-06-22 08:35:33Z ttsiodras $"  # pragma: no cover

# All the ada B mapper is now Obsolete, we are using ASN1SCC for Dumpables
#
# class FromDumpableCtoASN1SCC(RecursiveMapper):
#     def __init__(self):
#       self.uniqueID = 0
#     def UniqueID(self):
#       self.uniqueID += 1
#       return self.uniqueID
#     def DecreaseUniqueID(self):
#       self.uniqueID -= 1
#     def MapInteger(self, srcCVariable, destVar, _, __, ___):
#       return ["%s = %s;\n" % (destVar, srcCVariable)]
#     def MapReal(self, srcCVariable, destVar, _, __, ___):
#       return ["%s = %s;\n" % (destVar, srcCVariable)]
#     def MapBoolean(self, srcCVariable, destVar, _, __, ___):
#       return ["%s = %s;\n" % (destVar, srcCVariable)]
#     def MapOctetString(self, srcCVariable, destVar, _, __, ___):
#       lines = []
#       lines.append("{\n")
#       lines.append("    int i;\n")
#       lines.append("    for(i=0; i<%s.length; i++)\n" % srcCVariable)
#       lines.append("        %s.arr[i] = %s.content[i];\n" % (destVar, srcCVariable))
#       lines.append("    %s.nCount = %s.length;\n" % (destVar, srcCVariable))
#       lines.append("}\n")
#       return lines
#     def MapEnumerated(self, srcCVariable, destVar, _, __, ___):
#       return ["%s = %s;\n" % (destVar, srcCVariable)]
#     def MapSequence(self, srcCVariable, destVar, node, leafTypeDict, names):
#       lines = []
#       for child in node._members:
#           lines.extend(
#               self.Map(
#                   "%s.%s" % (srcCVariable, self.CleanName(child[0])),
#                   destVar + "." + self.CleanName(child[0]),
#                   child[1],
#                   leafTypeDict,
#                   names))
#       return lines
#     def MapSet(self, srcCVariable, destVar, node, leafTypeDict, names):
#       return self.MapSequence(srcCVariable, destVar, node, leafTypeDict, names)
#     def MapChoice(self, srcCVariable, destVar, node, leafTypeDict, names):
#       lines = []
#       childNo = 0
#       for child in node._members:
#           childNo += 1
#           lines.append("%sif (%s.choiceIdx == %d) {\n" %
#               (self.maybeElse(childNo), srcCVariable, childNo))
#           lines.extend(['    '+x for x in self.Map(
#                   "%s.u.%s" % (srcCVariable, self.CleanName(child[0])),
#                   destVar + ".u." + self.CleanName(child[0]),
#                   child[1],
#                   leafTypeDict,
#                   names)])
#           lines.append("    %s.kind = %s_PRESENT;\n" % (destVar, self.CleanName(child[0])))
#           lines.append("}\n")
#       return lines
#     def MapSequenceOf(self, srcCVariable, destVar, node, leafTypeDict, names):
#       lines = []
#       lines.append("{\n")
#       uniqueId = self.UniqueID()
#       lines.append("    int i%s;\n" % uniqueId)
#       lines.append("    for(i%s=0; i%s<%s.length; i%s++) {\n" % (uniqueId, uniqueId, srcCVariable, uniqueId))
#       lines.extend(["        " + x for x in self.Map(
#               "%s.content[i%s]" % (srcCVariable, uniqueId),
#               "%s.arr[i%s]" % (destVar, uniqueId),
#               node._containedType,
#               leafTypeDict,
#               names)])
#       lines.append("    }\n")
#       lines.append("    %s.nCount = %s.length;\n" % (destVar, srcCVariable))
#       lines.append("}\n")
#       self.DecreaseUniqueID()
#       return lines
#     def MapSetOf(self, srcCVariable, destVar, node, leafTypeDict, names):
#       return self.MapSequenceOf(srcCVariable, destVar, node, leafTypeDict, names)
#
# class FromASN1SCCtoDumpableC(RecursiveMapper):
#     def __init__(self):
#       self.uniqueID = 0
#     def UniqueID(self):
#       self.uniqueID += 1
#       return self.uniqueID
#     def DecreaseUniqueID(self):
#       self.uniqueID -= 1
#     def MapInteger(self, srcCVariable, destVar, _, __, ___):
#       return ["%s = %s;\n" % (destVar, srcCVariable)]
#     def MapReal(self, srcCVariable, destVar, _, __, ___):
#       return ["%s = %s;\n" % (destVar, srcCVariable)]
#     def MapBoolean(self, srcCVariable, destVar, _, __, ___):
#       return ["%s = %s;\n" % (destVar, srcCVariable)]
#     def MapOctetString(self, srcCVariable, destVar, _, __, ___):
#       lines = []
#       lines.append("{\n")
#       lines.append("    int i;\n")
#       lines.append("    for(i=0; i<%s.nCount; i++)\n" % srcCVariable)
#       lines.append("        %s.content[i] = %s.arr[i];\n" % (destVar, srcCVariable))
#       lines.append("    %s.length = %s.nCount;\n" % (destVar, srcCVariable))
#       lines.append("}\n")
#       return lines
#     def MapEnumerated(self, srcCVariable, destVar, _, __, ___):
#       return ["%s = %s;\n" % (destVar, srcCVariable)]
#     def MapSequence(self, srcCVariable, destVar, node, leafTypeDict, names):
#       lines = []
#       for child in node._members:
#           lines.extend(
#               self.Map(
#                   "%s.%s" % (srcCVariable, self.CleanName(child[0])),
#                   destVar + "." + self.CleanName(child[0]),
#                   child[1],
#                   leafTypeDict,
#                   names))
#       return lines
#     def MapSet(self, srcCVariable, destVar, node, leafTypeDict, names):
#       return self.MapSequence(srcCVariable, destVar, node, leafTypeDict, names)
#     def MapChoice(self, srcCVariable, destVar, node, leafTypeDict, names):
#       lines = []
#       childNo = 0
#       for child in node._members:
#           childNo += 1
#           lines.append("%sif (%s.kind == %s_PRESENT) {\n" %
#               (self.maybeElse(childNo), srcCVariable, self.CleanName(child[0])))
#           lines.extend(['    '+x for x in self.Map(
#                   "%s.u.%s" % (srcCVariable, self.CleanName(child[0])),
#                   destVar + ".u." + self.CleanName(child[0]),
#                   child[1],
#                   leafTypeDict,
#                   names)])
#           lines.append("    %s.choiceIdx = %d;\n" % (destVar, childNo))
#           lines.append("}\n")
#       return lines
#     def MapSequenceOf(self, srcCVariable, destVar, node, leafTypeDict, names):
#       lines = []
#       lines.append("{\n")
#       uniqueId = self.UniqueID()
#       lines.append("    int i%s;\n" % uniqueId)
#       lines.append("    for(i%s=0; i%s<%s.nCount; i%s++) {\n" % (uniqueId, uniqueId, srcCVariable, uniqueId))
#       lines.extend(["        " + x for x in self.Map(
#               "%s.arr[i%s]" % (srcCVariable, uniqueId),
#               "%s.content[i%s]" % (destVar, uniqueId),
#               node._containedType,
#               leafTypeDict,
#               names)])
#       lines.append("    }\n")
#       lines.append("    %s.length = %s.nCount;\n" % (destVar, srcCVariable))
#       lines.append("}\n")
#       self.DecreaseUniqueID()
#       return lines
#     def MapSetOf(self, srcCVariable, destVar, node, leafTypeDict, names):
#       return self.MapSequenceOf(srcCVariable, destVar, node, leafTypeDict, names)
#
# class Ada_GlueGenerator(ASynchronousToolGlueGenerator):
#     def __init__(self):
#       ASynchronousToolGlueGenerator.__init__(self)
#       self.FromDumpableCtoASN1SCC = FromDumpableCtoASN1SCC()
#       self.FromASN1SCCtoDumpableC = FromASN1SCCtoDumpableC()
#       self.Ada_HeaderFile = None
#       self.Ada_SourceFile = None
#       self.definedTypes = {}
#     def Version(self):
#       print "Code generator: " + "$Id: ada_B_mapper.py 2382 2012-06-22 08:35:33Z ttsiodras $"
#     def HeadersOnStartup(self, unused_asnFile, unused_outputDir, unused_maybeFVname):
#       if self.useOSS:
#           self.C_HeaderFile.write("#include \"%s.oss.h\" // OSS generated\n\n" % self.asn_name)
#           self.C_SourceFile.write("\nextern OssGlobal *g_world;\n\n")
#       self.C_HeaderFile.write("#include \"%s.h\" // Space certified compiler generated\n\n" % self.asn_name)
#       self.C_HeaderFile.write("#include \"DumpableTypes.h\"\n\n")
#     def Encoder(self, nodeTypename, node, leafTypeDict, names, encoding):
#       if encoding.lower() not in self.supportedEncodings:
#           panic(str(self.__class__) + ": in (%s), encoding can be one of %s (not '%s')" %
#               (nodeTypename, self.supportedEncodings, encoding))
#
#       # Definition of the standard encoding function (same interface as the C mapper )
#       cBackend.Encoder(nodeTypename, node, leafTypeDict, names, encoding)
#       # End standard encoding function
#
#                 # in order not to duplicate conversion functions, skip the rest if encoding is native
#       if encoding.lower() == "native":
#           return
#
#       if not self.definedTypes.has_key(nodeTypename):
#           self.definedTypes[nodeTypename] = 1
#           # Declare/define the C stub variable (one per ASN.1 type)
#           self.C_HeaderFile.write("\n/* --- Staging var for %s --- */\n" % (nodeTypename))
#
#       tmpTypeName = "asn1Scc%s" % self.CleanNameAsToolWants(nodeTypename)
#       tmpVarName = "asn1scc"
#       tmpSpName = "Ada_to_SCC_%s" % \
#           self.CleanNameAsToolWants(nodeTypename)
#
#       self.C_HeaderFile.write(
#           "void %s(GT__%s *ada, %s *%s);\n" %
#               (tmpSpName,
#               self.CleanNameAsToolWants(nodeTypename),
#               tmpTypeName,
#               tmpVarName))
#       self.C_SourceFile.write(
#           "void %s(GT__%s *ada, %s *%s)\n{\n" %
#               (tmpSpName,
#               self.CleanNameAsToolWants(nodeTypename),
#               tmpTypeName,
#               tmpVarName))
#
#       lines = self.FromDumpableCtoASN1SCC.Map(
#               "(*ada)",
#               "(*asn1scc)",
#               node,
#               leafTypeDict,
#               names)
#       lines = ["    "+x for x in lines]
#
#       self.C_SourceFile.write("".join(lines))
#       self.C_SourceFile.write("}\n\n")
#
#     def Decoder(self, nodeTypename, node, leafTypeDict, names, encoding):
#       if encoding.lower() not in self.supportedEncodings:
#           panic(str(self.__class__) + ": in (%s), encoding can be one of %s (not '%s')" %
#               (nodeTypename, self.supportedEncodings, encoding))
#
#       # Definition of the standard decoding function (same interface as the C mapper )
#       cBackend.Decoder(nodeTypename, node, leafTypeDict, names, encoding)
#       # End standard decoding function
#
#       if encoding.lower() == "native":
#           return
#
#       tmpTypeName = "asn1Scc%s" % self.CleanNameAsToolWants(nodeTypename)
#       tmpVarName = "asn1scc"
#       tmpSpName = "SCC_to_Ada_%s" % self.CleanNameAsToolWants(nodeTypename)
#
#       # Create C function that does the encoding
#       self.C_HeaderFile.write(
#           "void %s(%s *%s, GT__%s *ada);\n" %
#               (tmpSpName,
#               tmpTypeName,
#               tmpVarName,
#               self.CleanNameAsToolWants(nodeTypename)))
#       self.C_SourceFile.write(
#           "void %s(%s *%s, GT__%s *ada)\n{\n" %
#               (tmpSpName,
#               tmpTypeName,
#               tmpVarName,
#               self.CleanNameAsToolWants(nodeTypename)))
#
#       lines = self.FromASN1SCCtoDumpableC.Map(
#               "(*asn1scc)",
#               "(*ada)",
#               node,
#               leafTypeDict,
#               names)
#       lines = ["        "+x for x in lines]
#
#       self.C_SourceFile.write("".join(lines))
#       self.C_SourceFile.write("}\n\n")
#
#     def OnShutdown(self, modelingLanguage, asnFile, maybeFVname):
#       ASynchronousToolGlueGenerator.OnShutdown(self, modelingLanguage, asnFile, maybeFVname)


def OnStartup(unused_modelingLanguage, asnFile, outputDir, maybeFVname, useOSS):
    global cBackend
    # 2009-02-10: Since we now use ASN1SCC structures as dumpables (even for Ada)
    # we no longer need these Ada-specific Dumpable structures.
    #global adaBackend
    #adaBackend = Ada_GlueGenerator()
    cBackend = c_B_mapper.C_GlueGenerator()
    #adaBackend.OnStartup(modelingLanguage, asnFile, outputDir, maybeFVname, useOSS)
    cBackend.OnStartup("C", asnFile, outputDir, maybeFVname, useOSS)


def OnBasic(nodeTypename, node, leafTypeDict, names):
    cBackend.OnBasic(nodeTypename, node, leafTypeDict, names)


def OnSequence(nodeTypename, node, leafTypeDict, names):
    cBackend.OnSequence(nodeTypename, node, leafTypeDict, names)


def OnSet(nodeTypename, node, leafTypeDict, names):
    cBackend.OnSet(nodeTypename, node, leafTypeDict, names)  # pragma: nocover


def OnEnumerated(nodeTypename, node, leafTypeDict, names):
    cBackend.OnEnumerated(nodeTypename, node, leafTypeDict, names)


def OnSequenceOf(nodeTypename, node, leafTypeDict, names):
    cBackend.OnSequenceOf(nodeTypename, node, leafTypeDict, names)


def OnSetOf(nodeTypename, node, leafTypeDict, names):
    cBackend.OnSetOf(nodeTypename, node, leafTypeDict, names)  # pragma: nocover


def OnChoice(nodeTypename, node, leafTypeDict, names):
    cBackend.OnChoice(nodeTypename, node, leafTypeDict, names)


def OnShutdown(unused_modelingLanguage, asnFile, maybeFVname):
    cBackend.OnShutdown("C", asnFile, maybeFVname)
