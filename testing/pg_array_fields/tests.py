# -*- coding: utf-8 -*-

from django.contrib.admin import AdminSite, ModelAdmin
from django.core.serializers import serialize, deserialize
from django.test import TestCase

from djorm_expressions.base import SqlExpression
from djorm_pgarray.fields import ArrayField

from .forms import IntArrayForm
from .models import (IntModel, TextModel, DoubleModel, MTextModel,
                     MultiTypeModel, ChoicesModel, MacAddrModel)


class ArrayFieldTests(TestCase):
    def setUp(self):
        IntModel.objects.all().delete()
        TextModel.objects.all().delete()
        DoubleModel.objects.all().delete()
        MultiTypeModel.objects.all().delete()

    def test_empty_create(self):
        instance = IntModel.objects.create(lista=[])
        instance = IntModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.lista, [])

    def test_macaddr_model(self):
        instance = MacAddrModel.objects.create()
        instance.lista = ['00:24:d6:54:ff:c6', '00:24:d6:54:ff:c4']
        instance.save()

        instance = MacAddrModel.objects.get(pk=instance.pk)
        self.assertEqual(instance.lista, ['00:24:d6:54:ff:c6', '00:24:d6:54:ff:c4'])

    def test_overlap(self):
        obj1 = IntModel.objects.create(lista=[1,2,3])
        obj2 = IntModel.objects.create(lista=[2,4,5])
        obj3 = IntModel.objects.create(lista=[5,33,21])

        queryset = IntModel.objects.where(
            SqlExpression("lista", "&&", [1,2,3])
        )
        self.assertEqual(queryset.count(), 2)

        queryset = IntModel.objects.where(
            SqlExpression("lista", "&&", [1,2,3])
        )
        self.assertEqual(queryset.count(), 2)


    def test_contains_unicode(self):
        obj = TextModel.objects\
            .create(lista=[u"Fóö", u"Пример", u"test"])

        queryset = TextModel.objects.where(
            SqlExpression("lista", "@>", [u"Пример"])
        )
        self.assertEqual(queryset.count(), 1)

    def test_correct_behavior_with_text_arrays_01(self):
        obj = TextModel.objects.create(lista=[[1,2],[3,4]])
        obj = TextModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [[u'1', u'2'], [u'3', u'4']])

    def test_correct_behavior_with_text_arrays_02(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj = MTextModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])

    def test_correct_behavior_with_int_arrays(self):
        obj = IntModel.objects.create(lista=[1,2,3])
        obj = IntModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [1, 2, 3])

    def test_correct_behavior_with_float_arrays(self):
        obj = DoubleModel.objects.create(lista=[1.2,2.4,3])
        obj = DoubleModel.objects.get(pk=obj.pk)
        self.assertEqual(obj.lista, [1.2, 2.4, 3])

    def test_value_to_string_serializes_correctly(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj_int = IntModel.objects.create(lista=[1,2,3])

        serialized_obj = serialize('json', MTextModel.objects.filter(pk=obj.pk))
        serialized_obj_int = serialize('json', IntModel.objects.filter(pk=obj_int.pk))

        obj.delete()
        obj_int.delete()

        deserialized_obj = list(deserialize('json', serialized_obj))[0]
        deserialized_obj_int = list(deserialize('json', serialized_obj_int))[0]

        obj = deserialized_obj.object
        obj_int = deserialized_obj_int.object
        obj.save()
        obj_int.save()

        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])
        self.assertEqual(obj_int.lista, [1,2,3])

    def test_to_python_serializes_xml_correctly(self):
        obj = MTextModel.objects.create(data=[[u"1",u"2"],[u"3",u"ñ"]])
        obj_int = IntModel.objects.create(lista=[1,2,3])

        serialized_obj = serialize('xml', MTextModel.objects.filter(pk=obj.pk))
        serialized_obj_int = serialize('xml', IntModel.objects.filter(pk=obj_int.pk))

        obj.delete()
        obj_int.delete()
        deserialized_obj = list(deserialize('xml', serialized_obj))[0]
        deserialized_obj_int = list(deserialize('xml', serialized_obj_int))[0]
        obj = deserialized_obj.object
        obj_int = deserialized_obj_int.object
        obj.save()
        obj_int.save()

        self.assertEqual(obj.data, [[u"1",u"2"],[u"3",u"ñ"]])
        self.assertEqual(obj_int.lista, [1,2,3])

    def test_can_override_formfield(self):
        model_field = ArrayField()
        class FakeFieldClass(object):
            def __init__(self, *args, **kwargs):
                pass
        form_field = model_field.formfield(form_class=FakeFieldClass)
        self.assertIsInstance(form_field, FakeFieldClass)

    def test_other_types_properly_casted(self):
        obj = MultiTypeModel.objects.create(
            smallints=[1, 2, 3],
            varchars=['One', 'Two', 'Three']
        )
        obj = MultiTypeModel.objects.get(pk=obj.pk)

        self.assertEqual(obj.smallints, [1, 2, 3])
        self.assertEqual(obj.varchars, ['One', 'Two', 'Three'])

    def test_choices_validation(self):
        obj = ChoicesModel(choices=['A'])
        obj.full_clean()
        obj.save()


class ArrayFormFieldTests(TestCase):
    def test_regular_forms(self):
        form = IntArrayForm()
        self.assertFalse(form.is_valid())
        form = IntArrayForm({'lista':u'[1,2]'})
        self.assertTrue(form.is_valid())

    def test_empty_value(self):
        form = IntArrayForm({'lista':u''})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['lista'], [])

    def test_admin_forms(self):
        site = AdminSite()
        model_admin = ModelAdmin(IntModel, site)
        form_clazz = model_admin.get_form(None)
        form_instance = form_clazz()

        try:
            form_instance.as_table()
        except TypeError:
            self.fail('HTML Rendering of the form caused a TypeError')

    def test_invalid_error(self):
        form = IntArrayForm({'lista':1})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors['lista'],
            [u'Enter a list of values, joined by commas.  E.g. "a,b,c".']
            )
