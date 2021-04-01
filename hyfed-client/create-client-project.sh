project_name="$1"

if [ -z "${project_name}" ]
then
  echo "Usage: ./create-client-project project_name"
  exit
fi

echo "Creating project ${project_name} ..."

# Based on code from https://stackoverflow.com/questions/34420091/spinal-case-to-camel-case
ProjectName=$(echo "${project_name}" | sed -r 's/(^|_)(\w)/\U\2/g')

cp -r my_tool_client "${project_name}_client"
cp my_tool_client_gui.py "${project_name}_client_gui.py"

# rename files
mv "${project_name}_client/project/my_tool_client_project.py" "${project_name}_client/project/${project_name}_client_project.py"
mv "${project_name}_client/util/my_tool_algorithms.py" "${project_name}_client/util/${project_name}_algorithms.py"
mv "${project_name}_client/util/my_tool_parameters.py" "${project_name}_client/util/${project_name}_parameters.py"
mv "${project_name}_client/util/my_tool_steps.py" "${project_name}_client/util/${project_name}_steps.py"
mv "${project_name}_client/widget/my_tool_dataset_widget.py" "${project_name}_client/widget/${project_name}_dataset_widget.py"
mv "${project_name}_client/widget/my_tool_project_info_widget.py" "${project_name}_client/widget/${project_name}_project_info_widget.py"

# replace my_tool with project_name and MyTool with ProjectName
sed -i "s/my_tool/${project_name}/g" "${project_name}_client/project/${project_name}_client_project.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_client/project/${project_name}_client_project.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_client/util/${project_name}_algorithms.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_client/util/${project_name}_algorithms.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_client/util/${project_name}_parameters.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_client/util/${project_name}_parameters.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_client/util/${project_name}_steps.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_client/util/${project_name}_steps.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_client/widget/${project_name}_dataset_widget.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_client/widget/${project_name}_dataset_widget.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_client/widget/${project_name}_project_info_widget.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_client/widget/${project_name}_project_info_widget.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_client_gui.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_client_gui.py"