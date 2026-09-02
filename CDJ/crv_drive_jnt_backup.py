import maya.cmds as mc
import math

"""
crv_drive_jnt.py
Author: Alexandre MAURIER
Created: 02 / 09 / 2026
Version: 2.2.0
Description: Creates locators driven by one or several curves, and
             optionally builds aimed joints on top of those locators.

import CDJ.crv_drive_jnt as cdj
cdj.show_ui()

"""

WINDOW_NAME = 'crvDriveJnts_UI'


# ============================================================
# CORE CLASS
# ============================================================

class CrvDriveJnts(object):
    """Drives locators along one or several curves and, optionally,
    builds an aimed joint chain on top of the resulting locators."""

    def __init__(self,
                 loc_count=10,
                 orient_to_crv=True,
                 offset_parent_matrix=True,
                 loc_up_vector=True,
                 locked_up_vector=True,
                 locked_orientation=True,
                 upV_name='loc_up_vector',
                 aim_joints=True,
                 aim_joints_base='base_loc'):

        self.loc_count = loc_count
        self.orient_to_crv = orient_to_crv
        self.offset_parent_matrix = offset_parent_matrix
        self.loc_up_vector = loc_up_vector
        self.locked_up_vector = locked_up_vector
        self.locked_orientation = locked_orientation
        self.upV_name = upV_name
        self.aim_joints = aim_joints
        self.aim_joints_base = aim_joints_base

        self.up_vector = [0, 1, 0]
        self.created_locators = []
        self.created_joints = []

    # --------------------------------------------------------
    # LOCATORS
    # --------------------------------------------------------

    def create_locators(self, curves=None):
        """Runs the locator setup on the given curves (or the current
        selection). Returns the list of created locators."""

        curves = curves or mc.ls(selection=True)
        if not curves:
            mc.warning('Select at least one curve.')
            return []

        self.up_vector = self._get_up_vector()
        self.created_locators = []

        for crv in curves:
            shapes = mc.listRelatives(crv, shapes=True) or []
            if not shapes:
                mc.warning('{} has no shape, skipped.'.format(crv))
                continue

            self._process_curve(crv, shapes[0])

        return self.created_locators

    def _get_up_vector(self):
        if self.loc_up_vector:
            return mc.xform(self.upV_name, q=True, ws=True, matrix=True)[4:7]
        return [0, 1, 0]

    def _process_curve(self, d_crv, crv_shp):

        for i in range(self.loc_count):
            suffix = d_crv + str(i)

            poc = mc.createNode('pointOnCurveInfo', n='POC_' + suffix)
            cLoc = mc.spaceLocator(n='cLoc_' + suffix)[0]
            self.created_locators.append(cLoc)

            mc.connectAttr(crv_shp + '.worldSpace', poc + '.inputCurve')
            mc.setAttr(poc + '.turnOnPercentage', 1)
            mc.setAttr(poc + '.parameter', (1.0 / self.loc_count) * i)

            if not self.orient_to_crv:
                mc.connectAttr(poc + '.result.position', cLoc + '.translate')
                continue

            ff_mtx = self._build_orient_matrix(poc, suffix)
            self._connect_output(ff_mtx, cLoc, suffix)

            if self.locked_orientation:
                self._lock_orientation(ff_mtx)

    def _build_orient_matrix(self, poc, suffix):
        """Builds a fourByFourMatrix: translation + tangent (X axis) +
        up x tangent (Z axis) -> orientation along the curve."""

        ff_mtx = mc.createNode('fourByFourMatrix', n='ff_mtx_' + suffix)

        for axis, col in zip('XYZ', range(3)):
            mc.connectAttr(poc + '.result.position' + axis,
                            ff_mtx + '.in3' + str(col))
            mc.connectAttr(poc + '.result.tangent' + axis,
                            ff_mtx + '.in0' + str(col))

        vecProduct = mc.createNode('vectorProduct', n='vecProduct_' + suffix)
        norm_vecProd = mc.createNode('normalize', n='norm_vecProd_' + suffix)

        mc.setAttr(vecProduct + '.operation', 2)  # cross product
        mc.connectAttr(poc + '.result.tangent', norm_vecProd + '.input')
        mc.connectAttr(norm_vecProd + '.output', vecProduct + '.input2')

        for axis, col in zip('XYZ', range(3)):
            mc.connectAttr(vecProduct + '.output' + axis,
                            ff_mtx + '.in2' + str(col))

        if self.locked_up_vector:
            for val, col in zip(self.up_vector, range(3)):
                mc.setAttr(ff_mtx + '.in1' + str(col), val)

        return ff_mtx

    def _connect_output(self, ff_mtx, cLoc, suffix):
        """Outputs the matrix either via offsetParentMatrix or
        plain translate/rotate."""

        if self.offset_parent_matrix:
            mc.setAttr(cLoc + '.translate', 0, 0, 0)

            pck_mtx = mc.createNode('pickMatrix', n='pck_mtx_' + suffix)
            mc.connectAttr(ff_mtx + '.output', pck_mtx + '.inputMatrix')
            mc.connectAttr(pck_mtx + '.outputMatrix',
                            cLoc + '.offsetParentMatrix')
            mc.setAttr(pck_mtx + '.useScale', 0)
            mc.setAttr(pck_mtx + '.useShear', 0)
        else:
            dec_mtx = mc.createNode('decomposeMatrix', n='dec_mtx_' + suffix)
            mc.connectAttr(ff_mtx + '.output', dec_mtx + '.inputMatrix')
            mc.connectAttr(dec_mtx + '.outputTranslate', cLoc + '.translate')
            mc.connectAttr(dec_mtx + '.outputRotate', cLoc + '.rotate')

    @staticmethod
    def _lock_orientation(ff_mtx):
        """Disconnects every orientation input (keeps translation) so
        the matrix stops updating with the curve."""

        skip = {'in30', 'in31', 'in32'}
        for row in range(4):
            for col in range(4):
                attr = 'in{}{}'.format(row, col)
                if attr in skip:
                    continue
                plug = ff_mtx + '.' + attr
                source = mc.listConnections(plug, s=True, d=False, p=True)
                if source:
                    mc.disconnectAttr(source[0], plug)

    # --------------------------------------------------------
    # JOINTS
    # --------------------------------------------------------

    def create_joints(self, locators=None):
        """Builds a base/end joint chain aimed at each locator, or a
        single joint per locator when aim_joints is disabled."""

        locators = locators or self.created_locators
        if not locators:
            mc.warning('No locators to build joints from. '
                       'Create the locators first.')
            return []

        self.created_joints = []

        if not self.aim_joints:
            for loc in locators:
                self._create_simple_joint(loc)
            return self.created_joints

        if not mc.objExists(self.aim_joints_base):
            mc.warning('{} does not exist.'.format(self.aim_joints_base))
            return []

        base_pos = mc.xform(self.aim_joints_base, q=True, ws=True, t=True)

        for loc in locators:
            self._create_aimed_joint(loc, base_pos)

        return self.created_joints

    def _create_simple_joint(self, loc):
        loc_pos = mc.xform(loc, q=True, ws=True, t=True)
        mc.select(clear=True)
        jnt = mc.joint(n='jnt_' + loc, p=loc_pos)
        self.created_joints.append(jnt)

    def _create_aimed_joint(self, loc, base_pos):
        mc.select(clear=True)
        base_jnt = mc.joint(n='jnt_base_' + loc, p=base_pos)

        loc_pos = mc.xform(loc, q=True, ws=True, t=True)
        jnt_length = math.dist(loc_pos, base_pos) * 0.9

        end_jnt = mc.joint(n='jnt_end_' + loc)
        mc.xform(end_jnt, os=True, t=(jnt_length, 0, 0))

        aim_mtx = mc.createNode('aimMatrix', n='aim_mtx_' + loc)
        mc.connectAttr(base_jnt + '.worldMatrix', aim_mtx + '.inputMatrix')
        mc.disconnectAttr(base_jnt + '.worldMatrix', aim_mtx + '.inputMatrix')

        mc.connectAttr(loc + '.worldMatrix',
                        aim_mtx + '.primary.primaryTargetMatrix')

        if self.loc_up_vector:
            mc.connectAttr(self.upV_name + '.worldMatrix',
                            aim_mtx + '.secondary.secondaryTargetMatrix')
        else:
            for val, axis in zip(self.up_vector, 'XYZ'):
                mc.setAttr(aim_mtx + '.secondaryTargetVector' + axis, val)

        if self.offset_parent_matrix:
            mc.connectAttr(aim_mtx + '.outputMatrix',
                            base_jnt + '.offsetParentMatrix')
        else:
            dec_mtx = mc.createNode('decomposeMatrix', n='dec_mtx_' + loc)
            mc.connectAttr(aim_mtx + '.outputMatrix', dec_mtx + '.inputMatrix')
            mc.connectAttr(dec_mtx + '.outputRotate', base_jnt + '.rotate')

        self.created_joints.extend([base_jnt, end_jnt])


# ============================================================
# UI STATE
# ============================================================

_tool = None  # holds the last CrvDriveJnts instance, shared between buttons


def update_ui_state(*_args):
    orient = mc.checkBox(orient_cb, q=True, value=True)
    up_vector_enabled = mc.checkBox(loc_up_vector_cb, q=True, value=True)
    aim_enabled = mc.checkBox(aim_joints_cb, q=True, value=True)

    mc.checkBox(locked_up_vector_cb, e=True,
                enable=(orient and up_vector_enabled))
    mc.checkBox(locked_orientation_cb, e=True, enable=orient)
    mc.textField(up_vector_name_tf, e=True, enable=up_vector_enabled)
    mc.textField(aim_joints_base_tf, e=True, enable=aim_enabled)


def _build_tool():
    return CrvDriveJnts(
        orient_to_crv=mc.checkBox(orient_cb, q=True, value=True),
        offset_parent_matrix=mc.checkBox(offset_parent_cb, q=True, value=True),
        loc_up_vector=mc.checkBox(loc_up_vector_cb, q=True, value=True),
        locked_up_vector=mc.checkBox(locked_up_vector_cb, q=True, value=True),
        locked_orientation=mc.checkBox(locked_orientation_cb, q=True, value=True),
        upV_name=mc.textField(up_vector_name_tf, q=True, text=True),
        aim_joints=mc.checkBox(aim_joints_cb, q=True, value=True),
        aim_joints_base=mc.textField(aim_joints_base_tf, q=True, text=True),
    )


def create_setup(*_args):
    global _tool
    _tool = _build_tool()

    # All selected curves are processed in one go
    locators = _tool.create_locators()

    if locators:
        mc.select(locators)


def add_joints_setup(*_args):
    global _tool

    if _tool is None:
        mc.warning('Create the locators first.')
        return

    # Keep the tool's settings in sync with the UI before building joints
    _tool.offset_parent_matrix = mc.checkBox(offset_parent_cb, q=True, value=True)
    _tool.loc_up_vector = mc.checkBox(loc_up_vector_cb, q=True, value=True)
    _tool.upV_name = mc.textField(up_vector_name_tf, q=True, text=True)
    _tool.aim_joints = mc.checkBox(aim_joints_cb, q=True, value=True)
    _tool.aim_joints_base = mc.textField(aim_joints_base_tf, q=True, text=True)

    joints = _tool.create_joints()

    if joints:
        mc.select(joints)


def show_help(*_args):
    help_window = 'crvDriveJnts_Help'

    if mc.window(help_window, exists=True):
        mc.deleteUI(help_window)

    mc.window(help_window, title='CDJ Tool - Help',
              widthHeight=(430, 380), sizeable=True)

    mc.columnLayout(adjustableColumn=True, rowSpacing=10,
                     columnAttach=('both', 12))
    mc.separator(height=8, style='none')

    mc.scrollField(
        editable=False,
        wordWrap=True,
        height=320,
        text=(
            'Orient To Curve\n'
            '  Orients the locators along the curve tangent.\n\n'
            'Offset Parent Matrix\n'
            '  Drives the locator/joint via offsetParentMatrix instead\n'
            '  of a decomposeMatrix node.\n\n'
            'Loc Up Vector\n'
            '  Uses an existing locator as the up vector reference.\n\n'
            'Locked Up Vector\n'
            '  Bakes the up vector as static values on the matrix.\n\n'
            'Locked Orientation\n'
            '  Bakes the orientation of each locator.\n\n'
            'Aim Joints\n'
            '  Builds a base/end joint chain aimed from a base locator\n'
            '  toward each driven locator, instead of a single joint.\n'
            '  If unchecked, joints will just be parented under the.\n'
            '  locators.\n'
        )
    )

    mc.showWindow(help_window)


# ============================================================
# UI
# ============================================================

def show_ui():
    global orient_cb, offset_parent_cb, loc_up_vector_cb
    global locked_up_vector_cb, locked_orientation_cb, up_vector_name_tf
    global aim_joints_cb, aim_joints_base_tf

    if mc.window(WINDOW_NAME, exists=True):
        mc.deleteUI(WINDOW_NAME)

    mc.window(WINDOW_NAME, title='CDJ Tool', widthHeight=(340, 500),
              sizeable=True)

    mc.menuBarLayout()
    mc.menu(label='Help')
    mc.menuItem(label='Help', command=show_help)

    main = mc.columnLayout(adjustableColumn=True, rowSpacing=6,
                            columnAttach=('both', 14))

    mc.separator(height=5, style='none')

    # --- Orientation frame ------------------------------------
    mc.frameLayout(label='Orientation', collapsable=False,
                    marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)

    orient_cb = mc.checkBox(label='Orient To Curve', value=True,
                             changeCommand=update_ui_state)
    locked_orientation_cb = mc.checkBox(label='Locked Orientation',
                                         value=True)

    mc.setParent('..')
    mc.setParent('..')

    # --- Up vector frame ----------------------------------------
    mc.frameLayout(label='Up Vector', collapsable=False,
                    marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)

    loc_up_vector_cb = mc.checkBox(label='Use Locator As Up Vector',
                                    value=True,
                                    changeCommand=update_ui_state)
    locked_up_vector_cb = mc.checkBox(label='Locked Up Vector', value=True)

    mc.separator(height=4, style='none')
    mc.text(label='Up Vector Locator', align='left',
            font='smallPlainLabelFont')
    up_vector_name_tf = mc.textField(text='loc_up_vector')

    mc.setParent('..')
    mc.setParent('..')

    # --- Output frame ---------------------------------------------
    mc.frameLayout(label='Output', collapsable=False,
                    marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)

    offset_parent_cb = mc.checkBox(label='Use Offset Parent Matrix',
                                    value=True)

    mc.setParent('..')
    mc.setParent('..')

    mc.separator(height=10, style='none')

    mc.button(label='Create locators', height=36, backgroundColor=(0.2, 0.5, 0.7),
              command=create_setup)

    mc.separator(height=16, style='in')

    # --- Joints frame -----------------------------------------------
    mc.frameLayout(label='Joints', collapsable=False,
                    marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)

    aim_joints_cb = mc.checkBox(label='Aim Joints', value=True,
                                 changeCommand=update_ui_state)

    mc.separator(height=4, style='none')
    mc.text(label='Aim Base Locator', align='left',
            font='smallPlainLabelFont')
    aim_joints_base_tf = mc.textField(text='base_loc')

    mc.setParent('..')
    mc.setParent('..')

    mc.separator(height=10, style='none')

    mc.button(label='Add Joints', height=36,
              backgroundColor=(0.2, 0.5, 0.7),
              command=add_joints_setup)

    mc.separator(height=10, style='none')

    mc.setParent(main)
    mc.showWindow(WINDOW_NAME)

    update_ui_state()