import maya.cmds as mc
from . import cdj_locs
from . import cdj_jnt

WINDOW_NAME = 'crvDriveJnts_UI'
LOC_COUNT = 10

_created_locators = []


def update_ui_state(*_args):
    orient = mc.checkBox(orient_cb, q=True, value=True)
    up_vector_enabled = mc.checkBox(loc_up_vector_cb, q=True, value=True)
    aim_enabled = mc.checkBox(aim_joints_cb, q=True, value=True)

    mc.checkBox(locked_up_vector_cb, e=True, enable=(orient and up_vector_enabled))
    mc.checkBox(locked_orientation_cb, e=True, enable=orient)
    mc.textField(up_vector_name_tf, e=True, enable=up_vector_enabled)
    mc.textField(aim_joints_base_tf, e=True, enable=aim_enabled)


def create_setup(*_args):
    global _created_locators
    _created_locators = cdj_locs.create_locators(
        loc_count=LOC_COUNT,
        orient_to_crv=mc.checkBox(orient_cb, q=True, value=True),
        offset_parent_matrix=mc.checkBox(offset_parent_cb, q=True, value=True),
        loc_up_vector=mc.checkBox(loc_up_vector_cb, q=True, value=True),
        locked_up_vector=mc.checkBox(locked_up_vector_cb, q=True, value=True),
        locked_orientation=mc.checkBox(locked_orientation_cb, q=True, value=True),
        upV_name=mc.textField(up_vector_name_tf, q=True, text=True)
    )

    if _created_locators:
        mc.select(_created_locators)


def add_joints_setup(*_args):
    if not _created_locators:
        mc.warning('Create the locators first.')
        return

    joints = cdj_jnt.create_joints(
        locators=_created_locators,
        aim_joints=mc.checkBox(aim_joints_cb, q=True, value=True),
        aim_joints_base=mc.textField(aim_joints_base_tf, q=True, text=True),
        loc_up_vector=mc.checkBox(loc_up_vector_cb, q=True, value=True),
        upV_name=mc.textField(up_vector_name_tf, q=True, text=True),
        offset_parent_matrix=mc.checkBox(offset_parent_cb, q=True, value=True)
    )

    if joints:
        mc.select(joints)


def show_help(*_args):
    help_window = 'crvDriveJnts_Help'
    if mc.window(help_window, exists=True):
        mc.deleteUI(help_window)

    mc.window(help_window, title='CDJ Tool - Help', widthHeight=(430, 380), sizeable=True)
    mc.columnLayout(adjustableColumn=True, rowSpacing=10, columnAttach=('both', 12))
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
            '  If unchecked, joints will just be parented under the\n'
            '  locators.\n'
        )
    )
    mc.showWindow(help_window)


def show_ui():
    global orient_cb, offset_parent_cb, loc_up_vector_cb
    global locked_up_vector_cb, locked_orientation_cb, up_vector_name_tf
    global aim_joints_cb, aim_joints_base_tf

    if mc.window(WINDOW_NAME, exists=True):
        mc.deleteUI(WINDOW_NAME)

    mc.window(WINDOW_NAME, title='CDJ Tool', widthHeight=(340, 500), sizeable=True)

    mc.menuBarLayout()
    mc.menu(label='Help')
    mc.menuItem(label='Help', command=show_help)

    main = mc.columnLayout(adjustableColumn=True, rowSpacing=6, columnAttach=('both', 14))
    mc.separator(height=5, style='none')

    # Orientation frame
    mc.frameLayout(label='Orientation', collapsable=False, marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)
    orient_cb = mc.checkBox(label='Orient To Curve', value=True, changeCommand=update_ui_state)
    locked_orientation_cb = mc.checkBox(label='Locked Orientation', value=True)
    mc.setParent('..')
    mc.setParent('..')

    # Up vector frame
    mc.frameLayout(label='Up Vector', collapsable=False, marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)
    loc_up_vector_cb = mc.checkBox(label='Use Locator As Up Vector', value=True, changeCommand=update_ui_state)
    locked_up_vector_cb = mc.checkBox(label='Locked Up Vector', value=True)
    mc.separator(height=4, style='none')
    mc.text(label='Up Vector Locator', align='left', font='smallPlainLabelFont')
    up_vector_name_tf = mc.textField(text='loc_up_vector')
    mc.setParent('..')
    mc.setParent('..')

    # Output frame
    mc.frameLayout(label='Output', collapsable=False, marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)
    offset_parent_cb = mc.checkBox(label='Use Offset Parent Matrix', value=True)
    mc.setParent('..')
    mc.setParent('..')

    mc.separator(height=10, style='none')
    mc.button(label='Create locators', height=36, backgroundColor=(0.2, 0.5, 0.7), command=create_setup)
    mc.separator(height=16, style='in')

    # Joints frame
    mc.frameLayout(label='Joints', collapsable=False, marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)
    aim_joints_cb = mc.checkBox(label='Aim Joints', value=True, changeCommand=update_ui_state)
    mc.separator(height=4, style='none')
    mc.text(label='Aim Base Locator', align='left', font='smallPlainLabelFont')
    aim_joints_base_tf = mc.textField(text='base_loc')
    mc.setParent('..')
    mc.setParent('..')

    mc.separator(height=10, style='none')
    mc.button(label='Add Joints', height=36, backgroundColor=(0.2, 0.5, 0.7), command=add_joints_setup)
    mc.separator(height=10, style='none')

    mc.setParent(main)
    mc.showWindow(WINDOW_NAME)
    update_ui_state()