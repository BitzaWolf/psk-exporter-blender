#--------------------------------------------------------------------#
# .psk Exporter for Blender 3.x                                      |
#                                                                    |
# @bitzawolf                                                         |
#                                                                    |
# This exporter is only intended for Unreal Tournament 2004.         |
# Using this to export PSK files for other Unreal games is untested. |
#--------------------------------------------------------------------#

import bpy
import os
from struct import pack

bl_info = {
    "name": "Export Unreal Tournament 2004 Skeleton Mesh (.psk)",
    "author": "Bitzawolf",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "File > Export > UT2004 Mesh (.psk)",
    "description": "Export Unreal Tournament 2004 Skeleton Mesh",
    "warning": "",
    "wiki_url": "https://github.com/BitzaWolf/psk-exporter-blender",
    "category": "Import-Export",
}
    

class UEQuat:
    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        self.X = x
        self.Y = y
        self.Z = z
        self.W = w

    def __str__(self):
        return "UEQaut(%f,%f,%f,%f)" % (self.X, self.Y, self.Z, self.W)

    def export(self):
        return pack('<ffff', self.X, self.Y, self.Z, self.W)
    
class UEVector():
    def __init__(self, X=0.0, Y=0.0, Z=0.0):
        self.X = X
        self.Y = Y
        self.Z = Z

    def __eq__(self, other):
        return (self.X == other.X
            and self.Y == other.Y
            and self.Z == other.Z)
    
    def __str__(self):
        return "UEVector(%f,%f,%f)" % (self.X, self.Y, self.Z)

    def export(self):
        return pack('<fff', self.X, self.Y, self.Z)

class UEWedge():
    def __init__(self, i=0, u=0.0, v=0.0, m=0):
        self.pointIndex = i
        self.U = u
        self.V = v
        self.materialIndex = m
    
    def __eq__(self, other):
        return (self.pointIndex == other.pointIndex
            and self.U == other.U
            and self.V == other.V
            and self.materialIndex == other.materialIndex)
    
    def __str__(self):
        return "UEWedge: (%d, %f, %f, %d)" % (self.pointIndex, self.U, self.V, self.materialIndex)
    
    def export(self):
        return pack('<IffI', self.pointIndex, self.U, abs(1 - self.V), self.materialIndex)

class UEFace():
    def __init__(self, w1=0, w2=1, w3=2, m=0, am=0, s=1):
        self.wedge1 = w1
        self.wedge2 = w2
        self.wedge3 = w3
        self.material = m
        self.auxMaterial = am
        self.smoothing = s
    
    def __str__(self):
        return "UEFace: (%d, %d, %d, mat %d, %d, %d)" % (self.wedge1, self.wedge2, self.wedge3, self.material, self.auxMaterial, self.smoothing)
    
    def export(self):
        #print(self)
        return pack("<HHHBBI", self.wedge1, self.wedge2, self.wedge3, self.material, self.auxMaterial, self.smoothing)

class UEMaterial():
    def __init__(self, name):
        self.name = name
        
    def __eq__(self, other):
        self.name == other.name
        
    def __str__(self):
        return "UEMaterial: %s" % (self.name)
    
    def export(self):
        return pack("<64sIIIIII", bytes(self.name, 'utf-8'), 0, 0, 0, 0, 0, 0)

class UEBone:
    def __init__(self, bone, parentIndex = 0):
        UE_MULTIPLIER = 100 # vectors are scaled up x100
        
        self.name = bone.name
        self.Orientation = UEQuat()
        self.Position = UEVector(bone.head_local[0] * UE_MULTIPLIER, bone.head_local[1] * UE_MULTIPLIER, bone.head_local[2] * UE_MULTIPLIER)
        self.Size = UEVector()
        self.Length = bone.length
        self.childCount = len(bone.children)
        self.parent = parentIndex

    def __str__(self):
        return ("UEBone: %s " % self.name) + str(self.Orientation) + str(self.Position) + str(self.Size) + (" len: %f kidz: %d parentIndex: %d" % (self.Length, self.childCount, self.parent))

    def export(self):
        return pack("<64sIII", bytes(self.name, 'utf-8'), 0, self.childCount, self.parent) + self.Orientation.export() + self.Position.export() + pack("<f", self.Length) + self.Size.export()

class UEWeight:
    def __init__(self, weight=1.0, vertex=0, bone=0):
        self.weight = weight
        self.vertex = vertex
        self.bone = bone
    
    def export(self):
        return pack("<fII", self.weight, self.vertex, self.bone)

def exportPSK(filePath):
    print("+----------------+")
    print("Exporting PSK...")

    targetObj = bpy.context.object
    targetArmature = targetObj.data
    targetMesh = targetObj.data

    for kiddo in targetObj.children:
        if (kiddo.type == "MESH"):
            targetObj = kiddo
            targetMesh = kiddo.data

    verts = []
    wedges = []
    faces = []
    materials = []
    bones = []
    weights = []

    fileOut = open(filePath, 'w+b')

    fileOut.write(pack("<20sIII", b"ACTRHEAD", 0x0132B546, 0, 0))
    fileOut.write(pack("<20sIII", b"PNTS0000", 0, 12, len(targetMesh.vertices)))

    VERTEX_SCALE = 100 # UT2004 scalues scales up verts by 100 times

    for v in targetMesh.vertices:
        vec = UEVector(v.co[0] * VERTEX_SCALE, v.co[1] * VERTEX_SCALE, v.co[2] * VERTEX_SCALE)
        verts.append(vec)
        fileOut.write(vec.export())


    # Wedges (UVs)
    for poly in targetMesh.polygons:
        faceWedges = []
        for i in poly.loop_indices:
            loop = targetMesh.loops[i]
            for j, uvData in enumerate(targetMesh.uv_layers):
                wedge = UEWedge(loop.vertex_index, uvData.data[loop.index].uv[0], uvData.data[loop.index].uv[1], 0)
                duplicateWedge = 0
                wedgeIndex = 0
                for k, w in enumerate(wedges):
                    wedgeIndex = k
                    if (wedge == w):
                        duplicateWedge = 1
                        break
                if (not duplicateWedge):
                    wedges.append(wedge)
                    wedgeIndex = len(wedges) - 1
                faceWedges.append(wedgeIndex)
        faces.append(UEFace(faceWedges[2], faceWedges[1], faceWedges[0]))

    fileOut.write(pack("<20sIII", b"VTXW0000", 0, 16, len(wedges)))
    for wedge in wedges:
        fileOut.write(wedge.export())


    # Faces
    fileOut.write(pack("<20sIII", b"FACE0000", 0, 12, len(faces)))
    for face in faces:
        fileOut.write(face.export())


    # Materials
    fileOut.write(pack("<20sIII", b"MATT0000", 0, 88, len(targetMesh.materials)))
    for mat in targetMesh.materials:
        UEMat = UEMaterial(mat.name)
        materials.append(UEMat)
        fileOut.write(UEMat.export())

    # Bones
    fileOut.write(pack("<20sIII", b"REFSKELT", 0, 120, len(targetArmature.bones)))
    def recurseBones(parentIndex, bone):
        UEB = UEBone(bone, parentIndex)
        bones.append(UEB)
        myIndex = len(bones) - 1
        for kiddo in bone.children:
            recurseBones(myIndex, kiddo)

    recurseBones(0, targetArmature.bones[0])
    for bone in bones:
        fileOut.write(bone.export())

    # Weights
    fileOut.write(pack("<20sIII", b"RAWWEIGHTS", 0, 12, len(targetMesh.vertices)))
    for group in targetObj.vertex_groups:
        boneIndex = 0
        for bone in bones:
            if (bone.name == group.name):
                break
            boneIndex += 1
        for vertIndex in range(0, len(verts)):
            blenderVert = targetMesh.vertices[vertIndex]
            for vertGroup in blenderVert.groups:
                if (vertGroup.group == group.index):
                    weight = UEWeight(vertGroup.weight, vertIndex, boneIndex)
                    weights.append(weight)
    for weight in weights:
        fileOut.write(weight.export())


    fileOut.close()
    print("Export succcessful!")

# -------------------------------------------------------------------------------------------
#                                   Blender Addon Stuff
# -------------------------------------------------------------------------------------------
class ExportPskAddon(bpy.types.Operator):
    bl_idname = "export_ut2004.psk"
    bl_label = "Export UT2004 PSK"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    
    filepath: bpy.props.StringProperty('')
    
    @classmethod
    def poll(cls, context):
        return (
            context.active_object is not None #and it has an armature and a mesh TODO
        )
    
    def execute(self, context):
        exportPSK(self.filepath)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        print("Invoke")
        wm = context.window_manager
        wm.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menuFunction(self, context):
    self.layout.operator(ExportPskAddon.bl_idname, text="UT 2004 mesh (.psk)")

def register():
    bpy.utils.register_class(ExportPskAddon)
    bpy.types.TOPBAR_MT_file_export.append(menuFunction)

def unregister():
    bpy.utils.unregister_class(ExportPskAddon)
    bpy.types.TOPBAR_MT_file_export.remove(menuFunction)

if __name__ == "__main__":
    print("-------------------------------------------")
    register()
"""
Blender addon TODO
Check to make sure an armature object is selected and we can find the armature and mesh


Functional TODO
bone rotations . _ .
test bone orientation
test bone weight assignment
multiple material assignment
"""