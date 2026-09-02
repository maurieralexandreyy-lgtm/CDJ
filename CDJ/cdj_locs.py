import maya.cmds as mc


def create_locators(curves=None,
                    loc_count=10,
                    orient_to_crv=True,
                    offset_parent_matrix=True,
                    loc_up_vector=True,
                    locked_up_vector=True,
                    locked_orientation=True,
                    upV_name='loc_up_vector'):
    """Runs the locator setup on the given curves (or current selection)."""
    curves = curves or mc.ls(selection=True)
    if not curves:
        mc.warning('Select at least one curve.')
        return []

    up_vector = _get_up_vector(loc_up_vector, upV_name)
    created_locators = []

    for crv in curves:
        shapes = mc.listRelatives(crv, shapes=True) or []
        if not shapes:
            mc.warning('{} has no shape, skipped.'.format(crv))
            continue

        for i in range(loc_count):
            suffix = crv + str(i)
            poc = mc.createNode('pointOnCurveInfo', n='POC_' + suffix)
            cLoc = mc.spaceLocator(n='cLoc_' + suffix)[0]
            created_locators.append(cLoc)

            mc.connectAttr(shapes[0] + '.worldSpace', poc + '.inputCurve')
            mc.setAttr(poc + '.turnOnPercentage', 1)
            mc.setAttr(poc + '.parameter', (1.0 / loc_count) * i)

            if not orient_to_crv:
                mc.connectAttr(poc + '.result.position', cLoc + '.translate')
                continue

            ff_mtx = _build_orient_matrix(poc, suffix, locked_up_vector, up_vector)
            _connect_output(ff_mtx, cLoc, suffix, offset_parent_matrix)

            if locked_orientation:
                _lock_orientation(ff_mtx)

    return created_locators


def _get_up_vector(loc_up_vector, upV_name):
    if loc_up_vector and mc.objExists(upV_name):
        return mc.xform(upV_name, q=True, ws=True, matrix=True)[4:7]
    return [0, 1, 0]


def _build_orient_matrix(poc, suffix, locked_up_vector, up_vector):
    ff_mtx = mc.createNode('fourByFourMatrix', n='ff_mtx_' + suffix)

    for axis, col in zip('XYZ', range(3)):
        mc.connectAttr(poc + '.result.position' + axis, ff_mtx + '.in3' + str(col))
        mc.connectAttr(poc + '.result.tangent' + axis, ff_mtx + '.in0' + str(col))

    vecProduct = mc.createNode('vectorProduct', n='vecProduct_' + suffix)
    norm_vecProd = mc.createNode('normalize', n='norm_vecProd_' + suffix)

    mc.setAttr(vecProduct + '.operation', 2)
    mc.connectAttr(poc + '.result.tangent', norm_vecProd + '.input')
    mc.connectAttr(norm_vecProd + '.output', vecProduct + '.input2')

    for axis, col in zip('XYZ', range(3)):
        mc.connectAttr(vecProduct + '.output' + axis, ff_mtx + '.in2' + str(col))

    if locked_up_vector:
        for val, col in zip(up_vector, range(3)):
            mc.setAttr(ff_mtx + '.in1' + str(col), val)

    return ff_mtx


def _connect_output(ff_mtx, cLoc, suffix, offset_parent_matrix):
    if offset_parent_matrix:
        mc.setAttr(cLoc + '.translate', 0, 0, 0)
        pck_mtx = mc.createNode('pickMatrix', n='pck_mtx_' + suffix)
        mc.connectAttr(ff_mtx + '.output', pck_mtx + '.inputMatrix')
        mc.connectAttr(pck_mtx + '.outputMatrix', cLoc + '.offsetParentMatrix')
        mc.setAttr(pck_mtx + '.useScale', 0)
        mc.setAttr(pck_mtx + '.useShear', 0)
    else:
        dec_mtx = mc.createNode('decomposeMatrix', n='dec_mtx_' + suffix)
        mc.connectAttr(ff_mtx + '.output', dec_mtx + '.inputMatrix')
        mc.connectAttr(dec_mtx + '.outputTranslate', cLoc + '.translate')
        mc.connectAttr(dec_mtx + '.outputRotate', cLoc + '.rotate')


def _lock_orientation(ff_mtx):
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