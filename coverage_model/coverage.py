#!/usr/bin/env python

"""
@package 
@file coverage_model
@author Christopher Mueller
@brief 
"""

# http://collabedit.com/kkacp


# Notes:
# cell_map[cell_handle]=(0d_handles,)
# 0d_map[0d_handle]=(cell_handles,)
# ** Done via an association table of 2 arrays - indices are the alignment
#
# parameter values implicitly aligned to 0d handle array
#
# shape applied to 0d handle array
#
# cell is 'top level dimension'
#
# parameters can be implicitly aligned to cell array

# TODO: All implementation is 'pre-alpha' - intended primarily to flesh out the API (though some may stick around)

#CBM:TODO: Add type checking throughout all classes as determined appropriate, a la:
#@property
#def spatial_domain(self):
#    return self.__spatial_domain
#
#@spatial_domain.setter
#def spatial_domain(self, value):
#    if isinstance(value, AbstractDomain):
#        self.__spatial_domain = value

from coverage_model.basic_types import *
import numpy as np
import pickle

#################
# Coverage Objects
#################

class AbstractCoverage(AbstractIdentifiable):
    """
    Core data model, persistence, etc
    TemporalTopology
    SpatialTopology
    """
    def __init__(self):
        AbstractIdentifiable.__init__(self)


    @classmethod
    def save(cls, cov_obj, file_path, use_ascii=False):
        if not isinstance(cov_obj, AbstractCoverage):
            raise StandardError('cov_obj must be an instance or subclass of AbstractCoverage: object is {0}'.format(type(cov_obj)))

        with open(file_path, 'w') as f:
            pickle.dump(cov_obj, f, 0 if use_ascii else 2)

        print 'Saved coverage_model to \'{0}\''.format(file_path)

    @classmethod
    def load(cls, file_path):
        with open(file_path, 'r') as f:
            obj = pickle.load(f)

        if not isinstance(obj, AbstractCoverage):
            raise StandardError('loaded object must be an instance or subclass of AbstractCoverage: object is {0}'.format(type(obj)))

        print 'Loaded coverage_model from {0}'.format(file_path)
        return obj

    @classmethod
    def copy(cls, cov_obj, *args):
        if not isinstance(cov_obj, AbstractCoverage):
            raise StandardError('cov_obj must be an instance or subclass of AbstractCoverage: object is {0}'.format(type(cov_obj)))

        # Args need to have 1-n (ParameterContext, DomainOfApplication, DomainOfApplication,) tuples
        # Need to pull the range_dictionary, spatial_domain and temporal_domain from cov_obj (TODO: copies!!)
        # DOA's and PC's used to copy data - TODO: Need way of reshaping PC's?
        # NTK:
        ccov = SimplexCoverage(name='', range_dictionary=None, spatial_domain=None, temporal_domain=None)

        return ccov


class ViewCoverage(AbstractCoverage):
    # TODO: Implement
    """
    References 1 AbstractCoverage and applies a Filter
    """
    def __init__(self):
        AbstractCoverage.__init__(self)

        self.reference_coverage = ''
        self.structure_filter = StructureFilter()
        self.parameter_filter = ParameterFilter()

class ComplexCoverage(AbstractCoverage):
    # TODO: Implement
    """
    References 1-n coverages
    """
    def __init__(self):
        AbstractCoverage.__init__(self)
        self.coverages = []

class SimplexCoverage(AbstractCoverage):
    """
    
    """
    def __init__(self, name, range_dictionary, spatial_domain, temporal_domain=None):
        AbstractCoverage.__init__(self)

        self.name = name
        self.range_dictionary = range_dictionary
        self.spatial_domain = spatial_domain
        self.temporal_domain = temporal_domain or GridDomain(GridShape('temporal',[0]), None, None)
        self._range_context = RangeGroup()
        self._range_value = RangeGroup()
        self._pcmap = {}
        self._temporal_param_name = None

    def append_parameter(self, parameter_context):
        pname = parameter_context.name

        # Determine the correct array shape (default is the shape of the spatial_domain)
        # If there is only one extent in the spatial domain and it's size is 1, collapse to time only
        if len(self.spatial_domain.shape.extents) == 1 and self.spatial_domain.shape.extents[0] == 1:
            shp = self.temporal_domain.shape.extents
        else:
            shp = self.temporal_domain.shape.extents + self.spatial_domain.shape.extents

        # Assign the pname to the CRS (if applicable) and select the appropriate domain (default is the spatial_domain)
        dom = self.spatial_domain
        if not parameter_context.axis is None and AxisTypeEnum.is_member(parameter_context.axis, AxisTypeEnum.TIME):
            if self._temporal_param_name is None:
                self._temporal_param_name = pname
            else:
                raise StandardError("temporal_parameter already defined.")
            dom = self.temporal_domain
            shp = self.temporal_domain.shape.extents
            dom.crs.axes[parameter_context.axis] = parameter_context.name
        elif parameter_context.axis in self.spatial_domain.crs.axes:
            dom.crs.axes[parameter_context.axis] = parameter_context.name

        self._pcmap[pname] = (len(self._pcmap), parameter_context, dom)
        self._range_context[pname] = parameter_context
        setattr(self._range_context, pname, self._range_context[pname])
        self._range_value[pname] = RangeMember(shp, parameter_context)
        setattr(self._range_value, pname, self._range_value[pname])

    def get_parameter(self, param_name):
        if param_name in self._range_context:
            p = Parameter(self._range_context[param_name], self._pcmap[param_name][2], self._range_value[param_name])
            return p

    def list_parameters(self, coords_only=False, data_only=False):
        if coords_only:
            lst=[x for x, v in self._range_context.iteritems() if v.is_coord]
        elif data_only:
            lst=[x for x, v in self._range_context.iteritems() if not v.is_coord]
        else:
            lst=self._range_context.keys()
        lst.sort()
        return lst

    def insert_timesteps(self, count, origin=None):
        if not origin is None:
            raise SystemError('Only append is currently supported')

        # Expand the shape of the temporal_dimension
        shp = self.temporal_domain.shape
        shp.extents[0] += count

        # Expand the temporal dimension of each of the parameters that are temporal TODO: Indicate which are temporal!
        for n in self._pcmap:
            arr = self._range_value[n].content
            pc = self._range_context[n]
            narr = np.empty((count,) + arr.shape[1:], dtype=pc.param_type)
            narr.fill(pc.fill_value)
            arr = np.append(arr, narr, 0)
            self._range_value[n].content = arr

    def set_time_values(self, tdoa, values):
        return self.set_parameter_values(self._temporal_param_name, tdoa, None, values)

    def get_time_values(self, tdoa=None, return_value=None):
        return self.get_parameter_values(self._temporal_param_name, tdoa, None, return_value)

    @property
    def num_timesteps(self):
        return self.temporal_domain.shape.extents[0]

    def set_parameter_values(self, param_name, tdoa=None, sdoa=None, value=None):
        if not param_name in self._range_value:
            raise StandardError('Parameter \'{0}\' not found in coverage_model'.format(param_name))

        tdoa = _get_valid_DomainOfApplication(tdoa, self.temporal_domain.shape.extents)
        sdoa = _get_valid_DomainOfApplication(sdoa, self.spatial_domain.shape.extents)

        print 'temporal doa: {0}'.format(tdoa.slices)
        print 'spatial doa: {0}'.format(sdoa.slices)

        slice_ = []
        slice_.extend(tdoa.slices)
        slice_.extend(sdoa.slices)

        print 'Setting slice: {0}'.format(slice_)

        #TODO: Do we need some validation that slice_ is the same rank and/or shape as values?
        self._range_value[param_name][slice_] = value

    def get_parameter_values(self, param_name, tdoa=None, sdoa=None, return_value=None):
        if not param_name in self._range_value:
            raise StandardError('Parameter \'{0}\' not found in coverage'.format(param_name))

        return_value = return_value or np.zeros([0])

        tdoa = _get_valid_DomainOfApplication(tdoa, self.temporal_domain.shape.extents)
        sdoa = _get_valid_DomainOfApplication(sdoa, self.spatial_domain.shape.extents)

#        print 'temporal doa: {0}'.format(tdoa.slices)
#        print 'spatial doa: {0}'.format(sdoa.slices)

        slice_ = []
        slice_.extend(tdoa.slices)
        slice_.extend(sdoa.slices)

#        print 'Getting slice: {0}'.format(slice_)

        return_value = self._range_value[param_name][slice_]
        return return_value

    def get_parameter_context(self, param_name):
        if not param_name in self._range_context:
            raise StandardError('Parameter \'{0}\' not found in coverage'.format(param_name))

        return self._range_context[param_name]

    @property
    def info(self):
        lst = []
        indent = ' '
        lst.append('ID: {0}'.format(self._id))
        lst.append('Name: {0}'.format(self.name))
        lst.append('Temporal Domain:\n{0}'.format(self.temporal_domain.__str__(indent*2)))
        lst.append('Spatial Domain:\n{0}'.format(self.spatial_domain.__str__(indent*2)))

        lst.append('Parameters:')
        for x in self._range_value:
            lst.append('{0}{1} {2}\n{3}'.format(indent*2,x,self._range_value[x].shape,self._range_context[x].__str__(indent*4)))

        return '\n'.join(lst)

    def __str__(self):
        lst = []
        indent = ' '
        lst.append('ID: {0}'.format(self._id))
        lst.append('Name: {0}'.format(self.name))
        lst.append('TemporalDomain: Shape=>{0} Axes=>{1}'.format(self.temporal_domain.shape.extents, self.temporal_domain.crs.axes))
        lst.append('SpatialDomain: Shape=>{0} Axes=>{1}'.format(self.spatial_domain.shape.extents, self.spatial_domain.crs.axes))
        lst.append('Coordinate Parameters: {0}'.format(self.list_parameters(coords_only=True)))
        lst.append('Data Parameters: {0}'.format(self.list_parameters(coords_only=False, data_only=True)))

        return '\n'.join(lst)


#################
# Range Objects
#################

#TODO: Consider usage of Ellipsis in all this slicing stuff as well

class DomainOfApplication(object):

    def __init__(self, slices, topoDim=None):
        if slices is None:
            raise StandardError('\'slices\' cannot be None')
        self.topoDim = topoDim or 0

        if _is_valid_constraint(slices):
            if not np.iterable(slices):
                slices = [slices]

            self.slices = slices
        else:
            raise StandardError('\'slices\' must be either single, tuple, or list of slice or int objects')

    def __iter__(self):
        return self.slices.__iter__()

    def __len__(self):
        return len(self.slices)

def _is_valid_constraint(v):
    ret = False
    if isinstance(v, (slice, int)) or \
       (isinstance(v, (list,tuple)) and np.array([_is_valid_constraint(e) for e in v]).all()):
            ret = True

    return ret

def _get_valid_DomainOfApplication(v, valid_shape):
    """
    Takes the value to validate and a tuple representing the valid_shape
    """

    if v is None:
        if len(valid_shape) == 1:
            v = slice(None)
        else:
            v = [slice(None) for x in valid_shape]

    if not isinstance(v, DomainOfApplication):
        v = DomainOfApplication(v)

    return v

class RangeGroup(dict):
    """
    All the functionality of a built_in dict, plus uses setattr to expose dictionary members as attributes
    """
    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        setattr(self, key, self[key])

    def __delitem__(self, key):
        delattr(self, key)
        dict.__delitem__(self, key)

class RangeMember(object):
    """
    This is what would provide the "abstraction" between the in-memory model and the underlying persistence - all through __getitem__ and __setitem__
    Mapping between the "complete" domain and the storage strategy can happen here
    """

    def __init__(self, shape, pcontext):
        self._arr_obj = np.empty(shape)
        self._arr_obj.fill(pcontext.fill_value)

    @property
    def shape(self):
        return self._arr_obj.shape

    @property
    def content(self):
        return self._arr_obj

    @content.setter
    def content(self, value):
        self._arr_obj=value

    # CBM: First swack - see this for more possible checks: http://code.google.com/p/netcdf4-python/source/browse/trunk/netCDF4_utils.py
    def __getitem__(self, slice_):
        if not _is_valid_constraint(slice_):
            raise SystemError('invalid constraint supplied: {0}'.format(slice_))

        # First, ensure we're working with a tuple
        if not np.iterable(slice_):
            slice_ = (slice_,)
        elif not isinstance(slice_,tuple):
            slice_ = tuple(slice_)

        # Then make it's the correct shape TODO: Should reference the shape of the Domain object
        alen = len(self._arr_obj.shape)
        slen = len(slice_)
        if not slen == alen:
            if slen > alen:
                slice_ = slice_[:alen]
            else:
                for n in range(slen, alen):
                    slice_ += (slice(None,None,None),)

        return self._arr_obj[slice_]

    def __setitem__(self, slice_, value):
        if not _is_valid_constraint(slice_):
            raise SystemError('invalid constraint supplied: {0}'.format(slice_))

        # First, ensure we're working with a tuple
        if not np.iterable(slice_):
            slice_ = (slice_,)
        elif not isinstance(slice_,tuple):
            slice_ = tuple(slice_)

        # Then make it's the correct rank TODO: Should reference the rank of the Domain object
        alen = len(self._arr_obj.shape)
        slen = len(slice_)
        if not slen == alen:
            if slen > alen:
                slice_ = slice_[:alen]
            else:
                for n in range(slen, alen):
                    slice_ += (slice(None,None,None),)

        self._arr_obj[slice_] = value

    def __str__(self):
        return '{0}'.format(self._arr_obj.shape)

class RangeDictionary(AbstractIdentifiable):
    """
    Currently known as Taxonomy with respect to the Granule & RecordDictionary
    May be synonymous with RangeType
    """
    def __init__(self):
        AbstractIdentifiable.__init__(self)


#################
# Abstract Parameter Value Objects
#################

class AbstractParameterValue(AbstractBase):
    """

    """
    def __init__(self):
        AbstractBase.__init__(self)

class AbstractSimplexParameterValue(AbstractParameterValue):
    """

    """
    def __init__(self):
        AbstractParameterValue.__init__(self)

class AbstractComplexParameterValue(AbstractParameterValue):
    """

    """
    def __init__(self):
        AbstractParameterValue.__init__(self)


#################
# Abstract Parameter Type Objects
#################

class AbstractParameterType(AbstractIdentifiable):
    """

    """
    def __init__(self):
        AbstractIdentifiable.__init__(self)

class AbstractSimplexParameterType(AbstractParameterType):
    """

    """
    def __init__(self):
        AbstractParameterType.__init__(self)

class AbstractComplexParameterType(AbstractParameterType):
    """

    """
    def __init__(self):
        AbstractParameterType.__init__(self)


#################
# Parameter Objects
#################

class Parameter(AbstractIdentifiable):
    """

    """
    def __init__(self, parameter_context, shape, value):
        AbstractIdentifiable.__init__(self)
        self.context = parameter_context
        self.value = value
        self.shape = shape

    # Expose a couple of the context attributes at this level as "read only"
    @property
    def name(self):
        return self.context.name

    @property
    def is_coordinate(self):
        return self.context.is_coord



class ParameterContext(AbstractIdentifiable):
    # TODO: Need to incorporate some indication of if the parameter is a function of temporal, spatial, both, or None
    """

    """
    def __init__(self, name, is_coord=False, param_type=None, axis=None, fill_value=None, uom=None):
        AbstractIdentifiable.__init__(self)
        self.name = name
        self.is_coord = is_coord
        self.param_type = param_type or AbstractParameterType()
        self.axis = axis or None
        self.fill_value = fill_value or -999
        self.uom = uom or 'unspecified'

    def __str__(self, indent=None):
        indent = indent or ' '
        lst = []
        lst.append('{0}ID: {1}'.format(indent, self._id))
        lst.append('{0}Name: {1}'.format(indent, self.name))
        if self.is_coord:
            lst.append('{0}Is Coordinate: {1}'.format(indent, AxisTypeEnum._str_map[self.axis]))
        lst.append('{0}Type: {1}'.format(indent, self.param_type))
        lst.append('{0}Fill Value: {1}'.format(indent, self.fill_value))
        lst.append('{0}Unit of Measure: {1}'.format(indent, self.uom))

        return '\n'.join(lst)


#################
# CRS Objects
#################
class CRS(AbstractIdentifiable):
    """

    """
    def __init__(self, axis_labels):
        AbstractIdentifiable.__init__(self)
        self.axes=Axes()
        for l in axis_labels:
            # Add an axis member for the indicated axis
            try:
                self.axes[l] = None
            except KeyError as ke:
                raise SystemError('Unknown AxisType \'{0}\': {1}'.format(l,ke.message))

    @classmethod
    def standard_temporal(cls):
        return CRS([AxisTypeEnum.TIME])

    @classmethod
    def lat_lon_height(cls):
        return CRS([AxisTypeEnum.LON, AxisTypeEnum.LAT, AxisTypeEnum.HEIGHT])

    @classmethod
    def lat_lon(cls):
        return CRS([AxisTypeEnum.LON, AxisTypeEnum.LAT])

    @classmethod
    def x_y_z(cls):
        return CRS([AxisTypeEnum.GEO_X, AxisTypeEnum.GEO_Y, AxisTypeEnum.GEO_Z])

    def __str__(self, indent=None):
        indent = indent or ' '
        lst = []
        lst.append('{0}ID: {1}'.format(indent, self._id))
        lst.append('{0}Axes: {1}'.format(indent, self.axes))

        return '\n'.join(lst)

class Axes(dict):
    """
    Ensures that the indicated axis exists and that the string representation is used for the key
    """

    def __getitem__(self, item):
        if item in AxisTypeEnum._str_map:
            item = AxisTypeEnum._str_map[item]
        elif item in AxisTypeEnum._value_map:
            pass
        else:
            raise KeyError('Invalid axis key, must be a member of AxisTypeEnum')

        return dict.__getitem__(self, item)

    def __setitem__(self, key, value):
        if key in AxisTypeEnum._str_map:
            key = AxisTypeEnum._str_map[key]
        elif key in AxisTypeEnum._value_map:
            pass
        else:
            raise KeyError('Invalid axis key, must be a member of AxisTypeEnum')

        dict.__setitem__(self, key, value)

    def __contains__(self, item):
        if item in AxisTypeEnum._str_map:
            item = AxisTypeEnum._str_map[item]

        return dict.__contains__(self, item)

class AxisTypeEnum(object):
    """
    Temporarily taken from: http://www.unidata.ucar.edu/software/netcdf-java/v4.2/javadoc/ucar/nc2/constants/AxisType.html
    """
    # Ensemble represents the ensemble coordinate
    ENSEMBLE = 0

    # GeoX represents a x coordinate
    GEO_X = 1

    # GeoY represents a y coordinate
    GEO_Y = 2

    # GeoZ represents a z coordinate
    GEO_Z = 3

    # Height represents a vertical height coordinate
    HEIGHT = 4

    # Lat represents a latitude coordinate
    LAT = 5

    # Lon represents a longitude coordinate
    LON = 6

    # Pressure represents a vertical pressure coordinate
    PRESSURE = 7

    # RadialAzimuth represents a radial azimuth coordinate
    RADIAL_AZIMUTH = 8

    # RadialDistance represents a radial distance coordinate
    RADIAL_DISTANCE = 9

    # RadialElevation represents a radial elevation coordinate
    RADIAL_ELEVATION = 10

    # RunTime represents the runTime coordinate
    RUNTIME = 11

    # Time represents the time coordinate
    TIME = 12

    _value_map = {'ENSAMBLE':0, 'GEO_X':1 , 'GEO_Y':2, 'GEO_Z':3, 'HEIGHT':4, 'LAT':5, 'LON':6, 'PRESSURE':7, 'RADIAL_AZIMUTH':8, 'RADIAL_DISTANCE':9, 'RADIAL_ELEVATION':10, 'RUNTIME':11, 'TIME':12, }
    _str_map = {0:'ENSAMBLE', 1:'GEO_X' , 2:'GEO_Y', 3:'GEO_Z', 4:'HEIGHT', 5:'LAT', 6:'LON', 7:'PRESSURE', 8:'RADIAL_AZIMUTH', 9:'RADIAL_DISTANCE', 10:'RADIAL_ELEVATION', 11:'RUNTIME', 12:'TIME', }

    @classmethod
    def get_member(cls, value):
        if isinstance(value, int):
            return AxisTypeEnum.__getattribute__(cls, AxisTypeEnum._str_map[value])
        elif isinstance(value, (str,unicode)):
            return AxisTypeEnum.__getattribute__(cls, value.upper())
        else:
            raise TypeError('AxisTypeEnum has no member: {0}'.format(value))

    @classmethod
    def is_member(cls, value, want):
        v=AxisTypeEnum.get_member(value)
        return v == want

#################
# Domain Objects
#################

class MutabilityEnum(object):
    IMMUTABLE = 1
    EXTENSIBLE = 2
    MUTABLE = 3
    _value_map = {'IMMUTABLE': 1, 'EXTENSIBLE': 2, 'MUTABLE': 3,}
    _str_map = {1: 'IMMUTABLE', 2: 'EXTENSIBLE', 3: 'MUTABLE'}

    @classmethod
    def get_member(cls, value):
        if isinstance(value, int):
            return MutabilityEnum.__getattribute__(cls, MutabilityEnum._str_map[value])
        elif isinstance(value, (str,unicode)):
            return MutabilityEnum.__getattribute__(cls, value.upper())
        else:
            raise TypeError('AxisTypeEnum has no member: {0}'.format(value))

    @classmethod
    def is_member(cls, value, want):
        v=MutabilityEnum.get_member(value)
        return v == want

class AbstractDomain(AbstractIdentifiable):
    """

    """
    def __init__(self, shape, crs, mutability):
        AbstractIdentifiable.__init__(self)
        self.shape = shape
        self.crs = crs
        self.mutability = mutability or MutabilityEnum.IMMUTABLE

#    def get_mutability(self):
#        return self.mutability

    def get_max_dimension(self):
        pass

    def get_num_elements(self, dim_index):
        pass

#    def get_shape(self):
#        return self.shape

    def insert_elements(self, dim_index, count, doa):
        pass

    def __str__(self, indent=None):
        indent = indent or ' '
        lst=[]
        lst.append('{0}ID: {1}'.format(indent, self._id))
        lst.append('{0}Shape:\n{1}'.format(indent, self.shape.__str__(indent*2)))
        lst.append('{0}CRS:\n{1}'.format(indent, self.crs.__str__(indent*2)))
        lst.append('{0}Mutability: {1}'.format(indent, MutabilityEnum._str_map[self.mutability]))

        return '\n'.join(lst)

class GridDomain(AbstractDomain):
    """

    """
    def __init__(self, shape, crs, mutability=None):
        AbstractDomain.__init__(self, shape, crs, mutability)

class TopologicalDomain(AbstractDomain):
    """

    """
    def __init__(self):
        AbstractDomain.__init__(self)


#################
# Shape Objects
#################

class AbstractShape(AbstractIdentifiable):
    """

    """
    def __init__(self, name, extents=None):
        AbstractIdentifiable.__init__(self)
        self.name = name
        self.extents = extents or [1]

    @property
    def rank(self):
        return len(self.extents)

#    def rank(self):
#        return len(self.extents)

    def __str__(self, indent=None):
        indent = indent or ' '
        lst = []
        lst.append('{0}Extents: {1}'.format(indent, self.extents))

        return '\n'.join(lst)

class GridShape(AbstractShape):
    """

    """
    def __init__(self, name, extents=None):
        AbstractShape.__init__(self, name, extents)

    #CBM: Make extents type-safe


#################
# Filter Objects
#################

class AbstractFilter(AbstractIdentifiable):
    """

    """
    def __init__(self):
        AbstractIdentifiable.__init__(self)


class StructureFilter(AbstractFilter):
    """

    """
    def __init__(self):
        AbstractFilter.__init__(self)

class ParameterFilter(AbstractFilter):
    """

    """
    def __init__(self):
        AbstractFilter.__init__(self)



#################
# Possibly OBE ?
#################

#class Topology():
#    """
#    Sets of topological entities
#    Mappings between topological entities
#    """
#    pass
#
#class TopologicalEntity():
#    """
#
#    """
#    pass
#
#class ConstructionType():
#    """
#    Lattice or not (i.e. 'unstructured')
#    """
#    pass