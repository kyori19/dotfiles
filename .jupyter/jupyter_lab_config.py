# Configuration file for lab.

c = get_config()

# Remove outputs from notebooks on a device.
# https://jupyter-notebook.readthedocs.io/en/4.x/extending/savehooks.html#examples
#
# Unfortunately, this won't shorten save time due to large outputs.
def scrub_output_pre_save(model, **kwargs):
    # only run on notebooks
    if model['type'] != 'notebook' or model['content']['nbformat'] != 4:
        return

    for cell in model['content']['cells']:
        if cell['cell_type'] != 'code':
            continue
        cell['outputs'] = []
        cell['execution_count'] = None


c.ContentsManager.pre_save_hook = scrub_output_pre_save
