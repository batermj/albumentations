import random

import cv2

__all__ = ['to_tuple', 'BasicTransform', 'DualTransform', 'ImageOnlyTransform']


def to_tuple(param, low=None):
    if isinstance(param, tuple):
        return param
    else:
        return (-param if low is None else low, param)


def check_bboxes(bboxes):
    for index, bbox in enumerate(bboxes):
        for name, value in zip(['x_min', 'y_min', 'x_max', 'y_max'], bbox[:4]):
            if not 0 <= value <= 1:
                raise ValueError(
                    'Expected {name} for bbox {bbox} at index {index} '
                    'to be in the range [0.0, 1.0], got {value}.'.format(
                        bbox=bbox,
                        index=index,
                        name=name,
                        value=value,
                    )
                )
        x_min, y_min, x_max, y_max = bbox[:4]
        if x_max <= x_min:
            raise ValueError('x_max is less than or equal to x_min for bbox {bbox} at index {index}.'.format(
                bbox=bbox,
                index=index,
            ))
        if y_max <= y_min:
            raise ValueError('y_max is less than or equal to y_min for bbox {bbox} at index {index}.'.format(
                bbox=bbox,
                index=index,
            ))


class BasicTransform(object):
    def __init__(self, p=0.5):
        self.p = p

    def __call__(self, **kwargs):
        if random.random() < self.p:
            params = self.get_params()
            params = self.update_params(params, **kwargs)
            res = {}
            for key, arg in kwargs.items():
                target_function = self.targets.get(key, lambda x, **p: x)
                target_dependencies = {k: kwargs[k] for k in self.target_dependence.get(key, [])}
                res[key] = target_function(arg, **dict(params, **target_dependencies))
            return res
        return kwargs

    def apply(self, img, **params):
        raise NotImplementedError

    def get_params(self):
        return {}

    @property
    def targets(self):
        # you must specify targets in subclass
        # for example: ('image', 'mask')
        #              ('image', 'boxes')
        raise NotImplementedError

    def update_params(self, params, **kwargs):
        if hasattr(self, 'interpolation'):
            params['interpolation'] = self.interpolation
        params.update({'cols': kwargs['image'].shape[1], 'rows': kwargs['image'].shape[0]})
        return params

    @property
    def target_dependence(self):
        return {}


class DualTransform(BasicTransform):
    """Transform for segmentation task."""

    @property
    def targets(self):
        return {'image': self.apply, 'mask': self.apply_to_mask, 'bboxes': self.apply_to_bboxes}

    def apply_to_bbox(self, bbox, **params):
        raise NotImplementedError

    def apply_to_bboxes(self, bboxes, **params):
        bboxes = [list(bbox) for bbox in bboxes]
        check_bboxes(bboxes)
        return [self.apply_to_bbox(bbox[:4], **params) + bbox[4:] for bbox in bboxes]

    def apply_to_mask(self, img, **params):
        return self.apply(img, **{k: cv2.INTER_NEAREST if k == 'interpolation' else v for k, v in params.items()})


class ImageOnlyTransform(BasicTransform):
    """Transform applied to image only."""

    @property
    def targets(self):
        return {'image': self.apply}
