import maya.cmds as mc

"""
crv_drive_jnt.py
Author: Alexandre MAURIER
Created: 02 / 09 / 2026
Version: 2.0
Description: Creates locators driven by curves.


import crv_drive_jnt as cdj
cdj.show_ui()

"""


# PARAMETERS (defaults, overridden by the UI)

orient_to_crv = True
offset_parent_matrix = True
loc_up_vector = True
locked_up_vector = True
locked_orientation = True

upV_name = 'loc_up_vector'
LOC_COUNT = 10

###

WINDOW_NAME = 'crvDriveJnts_UI'

# CORE FUNCTION

def crv_drive_jnts():
    selection = mc.ls(selection=True)
    if not selection:
        mc.warning('Select a curve.')
        return

    d_crv = selection[0]
    crv_shp = mc.listRelatives(d_crv, shapes=True)[0]

    if loc_up_vector:
        up_vector = mc.xform(upV_name, q=True, ws=True, matrix=True)[4:7]
    else:
        up_vector = [0, 1, 0]

    for i in range(LOC_COUNT):
        suffix = d_crv + str(i)

        poc = mc.createNode('pointOnCurveInfo', n='POC_' + suffix)
        cLoc = mc.spaceLocator(n='cLoc_' + suffix)[0]

        mc.connectAttr(crv_shp + '.worldSpace', poc + '.inputCurve')
        mc.setAttr(poc + '.turnOnPercentage', 1)
        mc.setAttr(poc + '.parameter', (1.0 / LOC_COUNT) * i)

        if not orient_to_crv:
            mc.connectAttr(poc + '.result.position', cLoc + '.translate')
            continue

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

        if locked_up_vector:
            for val, col in zip(up_vector, range(3)):
                mc.setAttr(ff_mtx + '.in1' + str(col), val)

        # Output

        if offset_parent_matrix:
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


        if locked_orientation:
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

# UI

def update_ui_state(*_args):
    orient = mc.checkBox(orient_cb, q=True, value=True)
    up_vector_enabled = mc.checkBox(loc_up_vector_cb, q=True, value=True)

    mc.checkBox(locked_up_vector_cb, e=True,
                enable=(orient and up_vector_enabled))
    mc.checkBox(locked_orientation_cb, e=True, enable=orient)
    mc.textField(up_vector_name_tf, e=True, enable=up_vector_enabled)


def create_setup(*_args):
    global orient_to_crv, offset_parent_matrix, loc_up_vector
    global locked_up_vector, locked_orientation, upV_name

    orient_to_crv = mc.checkBox(orient_cb, q=True, value=True)
    offset_parent_matrix = mc.checkBox(offset_parent_cb, q=True, value=True)
    loc_up_vector = mc.checkBox(loc_up_vector_cb, q=True, value=True)
    locked_up_vector = mc.checkBox(locked_up_vector_cb, q=True, value=True)
    locked_orientation = mc.checkBox(locked_orientation_cb, q=True, value=True)
    upV_name = mc.textField(up_vector_name_tf, q=True, text=True)

    crv_drive_jnts()


def show_help(*_args):
    help_window = 'Help'

    if mc.window(help_window, exists=True):
        mc.deleteUI(help_window)

    mc.window(help_window,
              widthHeight=(420, 320), sizeable=True)

    mc.columnLayout(adjustableColumn=True, rowSpacing=10,
                     columnAttach=('both', 12))
    mc.separator(height=8, style='none')

    mc.scrollField(
        editable=False,
        wordWrap=True,
        height=260,
        text=(
            'Orient To Curve\n'
            '  Orients the locators along the curve tangent.\n\n'
            'Offset Parent Matrix\n'
            '  Drives the locator via offsetParentMatrix instead of\n'
            '  pluging in a decompose matrix node.\n\n'
            'Loc Up Vector\n'
            '  Uses an existing locator as the up vector reference.\n\n'
            'Locked Up Vector\n'
            '  Bakes the up vector as static values on the matrix.\n\n'
            'Locked Orientation\n'
            '  Bakes the orientation of each locator.\n'
        )
    )

    mc.showWindow(help_window)

###

def show_ui():
    global orient_cb, offset_parent_cb, loc_up_vector_cb
    global locked_up_vector_cb, locked_orientation_cb, up_vector_name_tf

    if mc.window(WINDOW_NAME, exists=True):
        mc.deleteUI(WINDOW_NAME)

    mc.window(WINDOW_NAME, title='CDJ Tool', widthHeight=(340, 400),
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

    orient_cb = mc.checkBox(label='Orient To Curve', value=orient_to_crv,
                             changeCommand=update_ui_state)
    locked_orientation_cb = mc.checkBox(label='Locked Orientation',
                                         value=locked_orientation)

    mc.setParent('..')
    mc.setParent('..')

    # --- Up vector frame ----------------------------------------
    mc.frameLayout(label='Up Vector', collapsable=False,
                    marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)

    loc_up_vector_cb = mc.checkBox(label='Use Locator As Up Vector',
                                    value=loc_up_vector,
                                    changeCommand=update_ui_state)
    locked_up_vector_cb = mc.checkBox(label='Locked Up Vector',
                                       value=locked_up_vector)

    mc.separator(height=4, style='none')
    mc.text(label='Up Vector Locator', align='left',
            font='smallPlainLabelFont')
    up_vector_name_tf = mc.textField(text=upV_name)

    mc.setParent('..')
    mc.setParent('..')

    # --- Output frame ---------------------------------------------
    mc.frameLayout(label='Output', collapsable=False,
                    marginWidth=10, marginHeight=8, labelAlign='top')
    mc.columnLayout(adjustableColumn=True, rowSpacing=6)

    offset_parent_cb = mc.checkBox(label='Use Offset Parent Matrix',
                                    value=offset_parent_matrix)

    mc.setParent('..')
    mc.setParent('..')

    mc.separator(height=14, style='none')

    mc.button(label='Create', height=36, backgroundColor=(0.2, 0.5, 0.7),
              command=create_setup)

    mc.separator(height=10, style='none')

    mc.setParent(main)
    mc.showWindow(WINDOW_NAME)

    update_ui_state()