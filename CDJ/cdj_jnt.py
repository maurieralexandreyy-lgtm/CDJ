import math
import maya.cmds as mc


def create_joints(locators,
                  aim_joints=True,
                  aim_joints_base='base_loc',
                  loc_up_vector=True,
                  upV_name='loc_up_vector',
                  offset_parent_matrix=True):
    """Builds a base/end joint chain aimed at each locator or single joints."""
    if not locators:
        mc.warning('No locators to build joints from. Create the locators first.')
        return []

    created_joints = []

    if not aim_joints:
        for loc in locators:
            loc_pos = mc.xform(loc, q=True, ws=True, t=True)
            mc.select(clear=True)
            mc.select(loc)
            jnt = mc.joint(n='jnt_' + loc, p=loc_pos)
            created_joints.append(jnt)
        return created_joints

    if not mc.objExists(aim_joints_base):
        mc.warning('{} does not exist.'.format(aim_joints_base))
        return []

    base_pos = mc.xform(aim_joints_base, q=True, ws=True, t=True)
    up_vector = mc.xform(upV_name, q=True, ws=True, matrix=True)[4:7] if (loc_up_vector and mc.objExists(upV_name)) else [0, 1, 0]

    for loc in locators:
        mc.select(clear=True)
        base_jnt = mc.joint(n='jnt_base_' + loc, p=base_pos)

        loc_pos = mc.xform(loc, q=True, ws=True, t=True)
        jnt_length = math.dist(loc_pos, base_pos) * 0.9

        end_jnt = mc.joint(n='jnt_end_' + loc)
        mc.xform(end_jnt, os=True, t=(jnt_length, 0, 0))

        aim_mtx = mc.createNode('aimMatrix', n='aim_mtx_' + loc)
        mc.connectAttr(base_jnt + '.worldMatrix', aim_mtx + '.inputMatrix')
        mc.disconnectAttr(base_jnt + '.worldMatrix', aim_mtx + '.inputMatrix')

        mc.connectAttr(loc + '.worldMatrix', aim_mtx + '.primary.primaryTargetMatrix')

        if loc_up_vector and mc.objExists(upV_name):
            mc.connectAttr(upV_name + '.worldMatrix', aim_mtx + '.secondary.secondaryTargetMatrix')
        else:
            for val, axis in zip(up_vector, 'XYZ'):
                mc.setAttr(aim_mtx + '.secondaryTargetVector' + axis, val)

        if offset_parent_matrix:
            mc.connectAttr(aim_mtx + '.outputMatrix', base_jnt + '.offsetParentMatrix')
        else:
            dec_mtx = mc.createNode('decomposeMatrix', n='dec_mtx_' + loc)
            mc.connectAttr(aim_mtx + '.outputMatrix', dec_mtx + '.inputMatrix')
            mc.connectAttr(dec_mtx + '.outputRotate', base_jnt + '.rotate')

        created_joints.extend([base_jnt, end_jnt])

    return created_joints