from .module_form import moduleForm, ModuleURLForm, ModuleEmbedForm
from .update_module_form import updatemoduleForm, UpdateModuleFileForm, UpdateModuleURLForm, UpdateModuleEmbedForm
from .copy_lesson_form import CopyLessonForm
from .subject_to_subject_copy_form import SubjectToSubjectCopyForm

__all__ = [
    # subject_to_subject_copy_form
    'SubjectToSubjectCopyForm', 

    # copy_lesson_form 
    'CopyLessonForm', 

    # module_form
    'moduleForm', 'ModuleURLForm', 'ModuleEmbedForm', 

    # update_module_form
    'updatemoduleForm', 'UpdateModuleFileForm', 'UpdateModuleURLForm', 'UpdateModuleEmbedForm',

]
