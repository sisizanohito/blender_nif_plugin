#!BPY

""" Registration info for Blender menus:
Name: 'NetImmerse/Gamebryo (.nif & .kf)...'
Blender: 239
Group: 'Import'
Tip: 'Import NIF (.nif & .kf) format meshes.'
"""

__author__ = "Alessandro Garosi (AKA Brandano) -- tdo_brandano@hotmail.com"
__url__ = ("blender", "elysiun", "http://niftools.sourceforge.net/")
__version__ = "1.2"
__bpydoc__ = """\
This script imports Netimmerse (the version used by Morrowind) .NIF files to Blender.
So far the script has been tested with 4.0.0.2 format files (Morrowind, Freedom Force).
There is a know issue with the import of .NIF files that have an armature; the file will import, but the meshes will be somewhat misaligned.

Usage:

Run this script from "File->Import" menu and then select the desired NIF file.

Options:

Scale Correction: How many NIF units is one Blender unit?

Vertex Duplication (Fast): Fast but imperfect: may introduce unwanted cracks in UV seams.

Vertex Duplication (Slow): Perfect but slow, this is the preferred method if the model you are importing is not too large.

Smoothing Flag (Slow): Import seams and convert them to "the Blender way", is slow and imperfect, unless model was created by Blender and had no duplicate vertices.

Tex Path: Semi-colon separated list of texture directories.
"""

# nif4_import.py version 1.2
# --------------------------------------------------------------------------
# ***** BEGIN LICENSE BLOCK *****
# 
# BSD License
# 
# Copyright (c) 2005, NIF File Format Library and Tools
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. The name of the NIF File Format Library and Tools project may not be
#    used to endorse or promote products derived from this software
#    without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ***** END LICENCE BLOCK *****
# Note: Versions of this script previous to 1.0.6 were released under the GPL license
# The script includes small portions of code obtained in the public domain, in particular
# the binary conversion functions. Every attempt to contact (or actually identify!) the
# original author has so far been fruitless.
# I have no claim of ownership these functions and will remove and replace them with
# a (probably less efficient) version if the original author ever will ask me to.
# --------------------------------------------------------------------------
#
# Credits:
# Portions of this programs are (were) derived (through the old tested method of cut'n paste)
# from the obj import script obj_import.py: OBJ Import v0.9 by Campbell Barton (AKA Ideasman)
# (No more. I rewrote the lot. Nevertheless I wouldn't have been able to start this without Ideasman's
# script to read from!)
# Binary conversion functions are courtesy of SJH. Couldn't find the full name, and couldn't find any
# license info, I got the code for these from http://projects.blender.org/pipermail/bf-python/2004-July/001676.html
# The file reading strategy was 'inspired' by the NifToPoly script included with the 
# DAOC mapper, which used to be available at http://www.randomly.org/projects/mapper/ and was written and 
# is copyright 2002 of Oliver Jowett. His domain and e-mail address are however no longer reacheable.
# No part of the original code is included here, as I pretty much rewrote everything, hence this is the 
# only mention of the original copyright. An updated version of the script is included with the DAOC Mappergui
# application, available at http://nathrach.republicofnewhome.org/mappergui.html
#
# Thanks go to:
# Campbell Barton (AKA Ideasman, Cambo) for making code clear enough to be used as a learning resource.
#   Hey, this is my first ever python script!
# SJH for the binary conversion functions. Got the code off a forum somewhere, posted by Ideasman,
#   I suppose it's allright to use it
# Lars Rinde (AKA Taharez), for helping me a lot with the file format, and with some debugging even
#   though he doesn't 'do Python'
# Timothy Wakeham (AKA timmeh), for taking some of his time to help me get to terms with the way
#   the UV maps work in Blender
# Amorilia (don't know your name buddy), for bugfixes and testing.



# Using the same setup as for Amorilia's exporter, so that the configuration can be shared, and to try
# sticking a little better to conventions
import Blender, sys
from Blender import BGL
from Blender import Draw
from Blender.Mathutils import *

try:
    from niflib import *
except:
    err = """--------------------------
ERROR\nThis script requires the NIFLIB Python SWIG wrapper, niflib.py & _niflib.dll.
Download it from http://niftools.sourceforge.net/
--------------------------"""
    print err
    Blender.Draw.PupMenu("ERROR%t|NIFLIB not found, check console for details")
    raise

global enableRe
enableRe = 1
try:
    import re
except:
    err = """--------------------------
ERROR\nThis script relies on the Regular Expression (re) module for some functionality.
advanced texture lookup will be disabled
--------------------------"""
    print err
    Blender.Draw.PupMenu("RE not found, check console for details")
    enableRe = 0


# dictionary of texture files, to reuse textures
global textures
textures = {}

# dictionary of materials, to reuse materials
global materials
materials = {}

# Regex to handle replacement texture files
if enableRe:
    re_dds = re.compile(r'^\.dds$', re.IGNORECASE)
    re_dds_subst = re.compile(r'^\.(tga|png|jpg|bmp|gif)$', re.IGNORECASE)
    

# 
# Process config files.
# 

NIF_VERSION_DICT = {}
NIF_VERSION_DICT['4.0.0.2']  = 0x04000002
NIF_VERSION_DICT['4.1.0.12'] = 0x0401000C
NIF_VERSION_DICT['4.2.0.2']  = 0x04020002
NIF_VERSION_DICT['4.2.1.0']  = 0x04020100
NIF_VERSION_DICT['4.2.2.0']  = 0x04020200
NIF_VERSION_DICT['10.0.1.0'] = 0x0A000100
NIF_VERSION_DICT['10.1.0.0'] = 0x0A010000
NIF_VERSION_DICT['10.2.0.0'] = 0x0A020000
NIF_VERSION_DICT['20.0.0.4'] = 0x14000004

# configuration default values
USE_GUI = 0
EPSILON = 0.005 # used for checking equality with floats, NOT STORED IN CONFIG
SCALE_CORRECTION = 10.0
FORCE_DDS = False
STRIP_TEXPATH = False
EXPORT_DIR = '' 
NIF_VERSION_STR = '4.0.0.2'
VERBOSE = True
CONFIRM_OVERWRITE = True

# tooltips
tooltips = {
    'SCALE_CORRECTION': "How many NIF units is one Blender unit?",
    'FORCE_DDS': "Force textures to be exported with a .DDS extension? Usually, you can leave this disabled.",
    'STRIP_TEXPATH': "Strip texture path in NIF file. You should leave this disabled, especially when this model's textures are stored in a subdirectory of the Data Files\Textures folder.",
    'EXPORT_DIR': "Default export directory.",
    'NIF_VERSION': "The NIF version to write."
}

# bounds
limits = {
    'SCALE_CORRECTION': [0.01, 100.0]
}

# update registry
def update_registry():
    # populate a dict with current config values:
    d = {}
    d['SCALE_CORRECTION'] = SCALE_CORRECTION
    d['FORCE_DDS'] = FORCE_DDS
    d['STRIP_TEXPATH'] = STRIP_TEXPATH
    d['EXPORT_DIR'] = EXPORT_DIR
    d['NIF_VERSION'] = NIF_VERSION_STR
    d['tooltips'] = tooltips
    d['limits'] = limits
    # store the key
    Blender.Registry.SetKey('nif_export', d, True)
    read_registry()

# Now we check if our key is available in the Registry or file system:
def read_registry():
    regdict = Blender.Registry.GetKey('nif_export', True)
    # If this key already exists, update config variables with its values:
    if regdict:
        try:
            SCALE_CORRECTION = regdict['SCALE_CORRECTION']
            FORCE_DDS = regdict['FORCE_DDS']
            STRIP_TEXPATH = regdict['STRIP_TEXPATH']
            EXPORT_DIR = regdict['EXPORT_DIR']
            NIF_VERSION_STR = regdict['NIF_VERSION']
            try:
                NIF_VERSION = NIF_VERSION_DICT[NIF_VERSION_STR]
            except:
                print "Warning: NIF version %s not supported; exporting version 4.0.0.2 instead."%NIF_VERSION_STR
                NIF_VERSION_STR = '4.0.0.2'
                NIF_VERSION = NIF_VERSION_DICT[NIF_VERSION_STR]
                raise # data was corrupted, reraise exception
        # if data was corrupted (or a new version of the script changed
        # (expanded, removed, renamed) the config vars and users may have
        # the old config file around):
        except: update_registry() # rewrite it
    else: # if the key doesn't exist yet, use our function to create it:
        update_registry()

read_registry()



# check General scripts config key for default behaviors
rd = Blender.Registry.GetKey('General', True)
if rd:
    try:
        VERBOSE = rd['verbose']
        CONFIRM_OVERWRITE = rd['confirm_overwrite']
    except: pass

# Little wrapper for debug messages
def msg(message='-', level=2):
    if VERBOSE:
        print message

#
# A simple custom exception class.
#
class NIFImportError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)




#
# Main import function.
#
def import_nif(filename):
    try: # catch NIFImportErrors
        global b_scene
        b_scene = Blender.Scene.GetCurrent()
        root_block = ReadNifTree(filename)
        # used to control the progress bar
        global block_count, blocks_read, read_progress
        block_count = BlocksInMemory()
        read_progress = 0.0
        blocks_read = 0.0
        read_branch(root_block)
        
    except NIFImportError, e: # in that case, we raise a menu instead of an exception
        Blender.Window.DrawProgressBar(1.0, "Import Failed")
        print 'NIFImportError: ' + e.value
        Blender.Draw.PupMenu('ERROR%t|' + e.value)
        return

    Blender.Window.DrawProgressBar(1.0, "Finished")
    
# Reads the content of the current NIF tree branch to Blender recursively
def read_branch(niBlock):
    global b_scene
    # used to control the progress bar
    global block_count, blocks_read, read_progress
    blocks_read += 1.0
    if (blocks_read/block_count) >= (read_progress + 0.1):
        read_progress = blocks_read/block_count
        Blender.Window.DrawProgressBar(read_progress, "Reading NIF file")
    if not niBlock.is_null():
        type=niBlock.GetBlockType()
        if type == "NiNode" or type == "RootCollisionNode":
            niChildren = niBlock["Children"].asLinkList()
            if (niBlock["Flags"].asInt() & 8) == 0 :
                # the node is a mesh influence
                #if inode.GetParent().asLink() is None or inode.GetParent().asLink()["Flags"].asInt() != 0x0002:
                #    # armature. The parent (can only be a NiNode) either doesn't exist or isn't an influence
                #    msg("%s is an armature" % fb_name(niBlock))
                #    children_list = []
                #    for child in [child for child in niChildren if child["Flags"].asInt() != 0x0002]:
                #        b_child = read_branch(child)
                #        if b_child: children_list.append(b_child)
                #    b_obj = fb_armature(niBlock)
                #    b_obj.makeParent(children_list)
                #    return b_obj
                #else:
                #    # bone. Do nothing, will be filled in by the armature
                    return None
            else:
                # grouping node
                b_obj = fb_empty(niBlock)
                b_children_list = []
                for child in niChildren:
                    b_child_obj = read_branch(child)
                    if b_child_obj: b_children_list.append(b_child_obj)
                b_obj.makeParent(b_children_list)
                b_obj.setMatrix(fb_matrix(niBlock))
                # set scale factor for root node
                b_obj.setMatrix(fb_matrix(niBlock)*fb_scale_mat())
        elif type == "NiTriShape":
            return fb_mesh(niBlock)
        else:
            return None

#
# Get unique name for an object, preserving existing names
#
def fb_name(niBlock):
    uniqueInt = 0
    niName = niBlock["Name"].asString()
    name = niName
    try:
        while Blender.Object.Get(name):
            name = '%s.%02d' % (niName, uniqueInt)
            uniqueInt +=1
    except:
        pass
    return name

def fb_matrix(niBlock):
    inode=QueryNode(niBlock)
    m=inode.GetLocalTransform()
    b_matrix_obj = Matrix([m[0][0],m[0][1],m[0][2],m[0][3]],
                        [m[1][0],m[1][1],m[1][2],m[1][3]],
                        [m[2][0],m[2][1],m[2][2],m[2][3]],
                        [m[3][0],m[3][1],m[3][2],m[3][3]])
    return b_matrix_obj

def fb_scale_mat():
    s = 1.0/SCALE_CORRECTION 
    return Matrix([s,0,0,0],[0,s,0,0],[0,0,s,0],[0,0,0,1])

def fb_empty(niBlock):
    global b_scene
    b_obj = Blender.Object.New("Empty", fb_name(niBlock))
    b_scene.link(b_obj)
    return b_obj
    
def fb_armature(niBlock):
    return fb_empty(niBlock)

# Creates and returns a mesh
def fb_mesh(niBlock):
    global b_scene
    seams_import = 0
    # Mesh name -> must be unique, so tag it if needed
    b_name=fb_name(niBlock)
    msg("whoot! %s" % b_name)
    # No getRaw, this time we work directly on Blender's objects
    b_meshData = Blender.Mesh.New(b_name)
    b_mesh = Blender.Object.New("Mesh", b_name)
    # Mesh transform matrix, sets the transform matrix for the object.
    b_mesh.setMatrix(fb_matrix(niBlock))
    # Mesh geometry data. From this I can retrieve all geometry info
    iShapeData = QueryShapeData(niBlock["Data"].asLink())
    iTriShapeData = QueryTriShapeData(niBlock["Data"].asLink())
    iTriStripsData = QueryTriStripsData(niBlock["Data"].asLink())
    #vertices
    if not iShapeData:
        raise NIFImportError("no iShapeData returned. Node name: %s " % b_name)
    verts = iShapeData.GetVertices()
    # Faces
    if iTriShapeData:
        faces = iTriShapeData.GetTriangles()
    elif iTriStripsData:
        faces = iTriStripsData.GetTriangles()
    else:
        raise NIFImportError("no iTri-Data returned. Node name: %s " % b_name)
    # "Sticky" UV coordinates. these are transformed in Blender UV's
    # only the first UV set is loaded right now
    hasVertexUV = False
    if iShapeData.GetUVSetCount()>0:
        hasVertexUV = True
        vertUV = iShapeData.GetUVSet(0)
    # Vertex colors
    vertCol = iShapeData.GetColors()
    hasVertexCol = len(vertCol)>0
    # Vertex normals
    vertNorms = iShapeData.GetNormals()
    # let's only duplicate vertices that have different
    # normals (to simulate sharp edges), so we build list of unique
    # (vertex, normal) pairs
    vertpairs = []
    vertmap = []
    for i in range(len(verts)):
        x = verts[i].x
        y = verts[i].y
        z = verts[i].z
        if vertNorms:
            nx = vertNorms[i].x
            ny = vertNorms[i].y
            nz = vertNorms[i].z
        found = 0
        if (seams_import == 1): 
            for j, vertpair in enumerate(vertpairs):
                if abs(x - vertpair[0][0]) > epsilon: continue
                if abs(y - vertpair[0][1]) > epsilon: continue
                if abs(z - vertpair[0][2]) > epsilon: continue
                if vertNorms:
                    if abs(nx - vertpair[1][0]) > epsilon: continue
                    if abs(ny - vertpair[1][1]) > epsilon: continue
                    if abs(nz - vertpair[1][2]) > epsilon: continue
                vertmap.append(j) # vertmap[i] = j
                found = 1
                break
        if found == 0:
            if vertNorms:
                vertpairs.append( ( verts[i], vertNorms[i] ) )
            else:
                vertpairs.append( ( verts[i], None ) )
            vertmap.append(len(vertpairs) - 1) # vertmap[i] = len(vertpairs) - 1
    # now import them
    for v, n in vertpairs:
        b_meshData.verts.extend(v.x, v.y, v.z)
        # let Blender calculate the vertex normals when doing meshData.update
        #if hasVertexNormals:
        #   nx, ny, nz = vertpair[1]
        #   meshData.verts[i].no[0] = nx
        #   meshData.verts[i].no[1] = ny
        #   meshData.verts[i].no[2] = nz
    for f in faces:
        #b_mesh.faces.extend([meshData.verts[vertmap[v1]], meshData.verts[vertmap[v2]], meshData.verts[vertmap[v3]]])
        b_meshData.faces.extend(b_meshData.verts[vertmap[f.v1]],b_meshData.verts[vertmap[f.v2]],b_meshData.verts[vertmap[f.v3]])
    for f in b_meshData.faces:
        f.smooth = 1
        #b_face.mat = 0
    
    # Vertex colors. For both this and UV mapping info I rely on the order of the faces matching that of the lists
    # passed as parameter to the function. Nasty but effective
    if hasVertexCol:
        meshData.hasVertexColours(1)
        for i, f in enumerate(faces):
            v1, v2, v3 = f
            for v in (v1, v2, v3):
                R, G, B, A = vertCol[v]
                R = int(R * 255)
                G = int(G * 255)
                B = int(B * 255)
                A = int(A * 255)
                b_mesh.faces[i].col.append(Blender.NMesh.Col(R, G, B, A))
        # vertex colors influence lighting...
        # so now we have to set the VCOL_LIGHT flag on the material
        # see below
    
    """
    # Nif files only support 'sticky' UV coordinates, and duplicates vertices to emulate hard edges and UV seams.
    # Essentially whenever an hard edge or an UV seam is present the mesh this is converted to an open mesh.
    # Blender also supports 'per face' UV coordinates, this could be a problem when exporting.
    # Also, NIF files support a series of texture sets, each one with its set of texture coordinates. For example
    # on a single "material" I could have a base texture, with a decal texture over it mapped on another set of UV
    # coordinates. I don't know if Blender can do the same.
    if hasVertexUV:
        # Sets the face UV's for the mesh on. The NIF format only supports vertex UV's,
        # but Blender only allows explicit editing of face UV's, so I'll load vertex UV's like face UV's
        meshData.hasFaceUV(1)
        meshData.hasVertexUV(0)
        for i in range(len(meshData.faces)):
            v1, v2, v3 = faces[i]
            meshData.faces[i].uv = []
            for v in (v1, v2, v3):
                (U, V) = vertUV[0][v]
                meshData.faces[i].uv.append((U, V))
    recalcNormals = 1
    if hasVertexNormals:
        recalcNormals = 0
    """
    """
    # Texturing property. From this I can retrieve texture info
    #texProperty = triShape.getNiTexturingProperty()
    # Material Property, from this I can retrieve material info
    #matProperty = triShape.getNiMaterialProperty()
    # Sets the material for this mesh. NIF files only support one material for each mesh
    if matProperty:
        material = createMaterial(matProperty, texProperty)
        # Alpha property
        alphaProperty = triShape.getNiAlphaProperty()
        # Texture. Only supports one atm
        mtex = material.getTextures()[0]
        # if the mesh has an alpha channel
        if alphaProperty:
            material.mode |= Material.Modes.ZTRANSP # enable z-buffered transparency
            # if the image has an alpha channel => then this overrides the material alpha value
            if mtex and mtex.tex.image.depth == 32: # ... crappy way to check for alpha channel in texture
                mtex.tex.imageFlags |= Blender.Texture.ImageFlags.USEALPHA # use the alpha channel
                mtex.mapto |=  Texture.MapTo.ALPHA # and map the alpha channel to transparency
                material.setAlpha(0.0) # for proper display in Blender, we must set the alpha value to 0 and the "Val" slider in the texture Map To tab to the NIF material alpha value (but we do not have access to that button yet... we have to wait until it gets supported by the Blender Python API...)
        else:
            # no alpha property: force alpha 1.0 in Blender
            material.setAlpha(1.0)
        if hasVertexCol:
            if mtex:
                material.mode |= Material.Modes.VCOL_LIGHT # textured material: vertex colors influence lighting
            else:
                material.mode |= Material.Modes.VCOL_PAINT # non-textured material: vertex colors incluence color
        meshData.addMaterial(material)
        #If there's a texture assigned to this material sets it to be displayed in Blender's 3D view
        if mtex:
            imgobj = mtex.tex.getImage()
            for f in meshData.faces: 
                f.image = imgobj
    """
    """
    # Skinning info, for meshes affected by bones. Adding groups to a mesh can be done only after this is already
    # linked to an object
    #skinInstance = triShape.getNiSkinInstance()
    if skinInstance:
        skinData = skinInstance.getNiSkinData()
        weights = skinData.getWeights()
        for idx, bone in enumerate(skinInstance.getBones()):
            if bone:
                groupName = bone.getName()
                meshData.addVertGroup(groupName)
                for vert, weight in weights[idx]:
                    vert2 = vertmap[vert]
                    meshData.assignVertsToGroup(groupName, [vert2], weight, 'replace')
    """
    """
    meshData.update(1) # let Blender calculate vertex normals
    """
    """
    # morphing
    #morphCtrl = triShape.getNiGeomMorpherController()
    if morphCtrl:
        morphData = morphCtrl.getNiMorphData()
        if morphData and ( morphData.NumMorphBlocks > 0 ):
            # insert base key
            meshData.insertKey( 0, 'relative' )
            frameCnt, frameType, frames, baseverts = morphData.MorphBlocks[0]
            ipo = Blender.Ipo.New( 'Key', 'KeyIpo' )
            # iterate through the list of other morph keys
            for key in range( 1, morphData.NumMorphBlocks ):
                frameCnt, frameType, frames, verts = morphData.MorphBlocks[key]
                # for each vertex calculate the key position from base pos + delta offset
                for count in range( morphData.NumVertices ):
                    x, y, z = baseverts[count]
                    dx, dy, dz = verts[count]
                    meshData.verts[vertmap[count]].co[0] = x + dx
                    meshData.verts[vertmap[count]].co[1] = y + dy
                    meshData.verts[vertmap[count]].co[2] = z + dz
                # update the mesh and insert key
                meshData.update(1) # recalculate normals
                meshData.insertKey(key, 'relative')
                # set up the ipo key curve
                curve = ipo.addCurve( 'Key %i'%key )
                # dunno how to set up the bezier triples -> switching to linear instead
                curve.setInterpolation( 'Linear' )
                # select extrapolation
                if ( morphCtrl.Flags == 0x000c ):
                    curve.setExtrapolation( 'Constant' )
                elif ( morphCtrl.Flags == 0x0008 ):
                    curve.setExtrapolation( 'Cyclic' )
                else:
                    debugMsg( 'dunno which extrapolation to use: using constant instead', 2 )
                    curve.setExtrapolation( 'Constant' )
                # set up the curve's control points
                for count in range( frameCnt ):
                    time, x, y, z = frames[count]
                    frame = time * Blender.Scene.getCurrent().getRenderingContext().framesPerSec() + 1
                    curve.addBezier( ( frame, x ) )
                # finally: return to base position
                for count in range( morphData.NumVertices ):
                    x, y, z = baseverts[count]
                    meshData.verts[vertmap[count]].co[0] = x
                    meshData.verts[vertmap[count]].co[1] = y
                    meshData.verts[vertmap[count]].co[2] = z
                meshData.update(1) # recalculate normals
            # assign ipo to mesh (not supported by Blender API?)
            #meshData.setIpo( ipo )
    """
    b_meshData.update()
    b_mesh.link(b_meshData)
    b_scene.link(b_mesh)
    return b_mesh




# calculate distance between two Float3 vectors
def get_distance(v, w):
    return ((v[0]-w[0])*(v[0]-w[0]) + (v[1]-w[1])*(v[1]-w[1]) + (v[2]-w[2])*(v[2]-w[2])) ** 0.5


#----------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------#
#-------- Run importer GUI.
#----------------------------------------------------------------------------------------------------#
#----------------------------------------------------------------------------------------------------#

def draw_gui():
    global Textbox2, Slider1, Textbox1
    global scale_correction,force_dds,strip_texpath,seams_import,last_imported,last_exported,user_texpath
    
    BGL.glClearColor(0.753, 0.753, 0.753, 0.0)
    BGL.glClear(BGL.GL_COLOR_BUFFER_BIT)

    BGL.glColor3f(0.000, 0.000, 0.000)
    BGL.glRasterPos2i(8, 92)
    Draw.Text('Tex Path:')
    BGL.glRasterPos2i(8, 188)
    Draw.Text('Seams:')

    Draw.Button('Browse', 1, 8, 48, 55, 23, '')
    Draw.Button('Import NIF', 2, 8, 8, 87, 23, '')
    Draw.Button('Cancel', 3, 208, 8, 71, 23, '')
    Draw.Toggle('Smoothing Flag (Slow)', 6, 88, 112, 191, 23, seams_import == 2, 'Import seams and convert them to "the Blender way", is slow and imperfect, unless model was created by Blender and had no duplicate vertices.')
    Draw.Toggle('Vertex Duplication (Slow)', 7, 88, 144, 191, 23, seams_import == 1, 'Perfect but slow, this is the preferred method if the model you are importing is not too large.')
    Draw.Toggle('Vertex Duplication (Fast)', 8, 88, 176, 191, 23, seams_import == 0, 'Fast but imperfect: may introduce unwanted cracks in UV seams')
    Textbox2 = Draw.String('', 4, 72, 80, 207, 23, user_texpath, 512, 'Semi-colon separated list of texture directories.')
    Textbox1 = Draw.String('', 5, 72, 48, 207, 23, last_imported, 512, '')
    Slider1 = Draw.Slider('Scale Correction: ', 9, 8, 208, 271, 23, scale_correction, 0.01, 100, 0, 'How many NIF units is one Blender unit?')

def event(evt, val):
    if (evt == Draw.QKEY and not val):
        Draw.Exit()

def bevent(evt):
    global Textbox2, Slider1, Textbox1
    global scale_correction,force_dds,strip_texpath,seams_import,last_imported,last_exported,user_texpath
    
    if evt == 6: #Toggle3
        seams_import = 2
        Draw.Redraw(1)
    elif evt == 7: #Toggle2
        seams_import = 1
        Draw.Redraw(1)
    elif evt == 8: #Toggle1
        seams_import = 0
        Draw.Redraw(1)
    elif evt == 1: # Browse
        Blender.Window.FileSelector(select, 'Select')
        Draw.Redraw(1)
    elif evt == 4: # TexPath
        user_texpath = Textbox2.val
    elif evt == 5: # filename
        last_imported = Textbox1.val
    elif evt == 9: # scale
        scale_correction = Slider1.val
    elif evt == 2: # Import NIF
        # Stop GUI.
        Textbox1 = None
        Textbox2 = None
        Slider1 = None
        Draw.Exit()
        # Save options for next time.
        configfile = open(configname, "w")
        configfile.write('scale_correction=%f\nforce_dds=%i\nstrip_texpath=%i\nseams_import=%i\nlast_imported=%s\nlast_exported=%s\nuser_texpath=%s\n'%(scale_correction,force_dds,strip_texpath,seams_import,last_imported,last_exported,user_texpath))
        configfile.close()
        # Import file.
        if seams_import == 2:
            debugMsg("Smoothing import not implemented yet, selecting slow vertex duplication method instead.", 1)
            seams_import = 1
        readFile(last_imported)
    elif evt == 3: # Cancel
        Textbox1 = None
        Textbox2 = None
        Slider1 = None
        Draw.Exit()

if USE_GUI:
    Draw.Register(draw_gui, event, bevent)
else:
    Blender.Window.FileSelector(import_nif, 'Import NIF', EXPORT_DIR)