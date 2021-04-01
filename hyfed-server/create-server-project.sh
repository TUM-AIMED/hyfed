project_name="$1"

if [ -z "${project_name}" ]
then
  echo "Usage: ./create-server-project project_name"
  exit
fi

echo "Creating project ${project_name} ..."

# Based on code from https://stackoverflow.com/questions/34420091/spinal-case-to-camel-case
ProjectName=$(echo "${project_name}" | sed -r 's/(^|_)(\w)/\U\2/g')

cp -r my_tool_server "${project_name}_server"

# rename files
mv "${project_name}_server/model/my_tool_model.py" "${project_name}_server/model/${project_name}_model.py"
mv "${project_name}_server/project/my_tool_server_project.py" "${project_name}_server/project/${project_name}_server_project.py"
mv "${project_name}_server/serializer/my_tool_serializers.py" "${project_name}_server/serializer/${project_name}_serializers.py"
mv "${project_name}_server/util/my_tool_algorithms.py" "${project_name}_server/util/${project_name}_algorithms.py"
mv "${project_name}_server/util/my_tool_parameters.py" "${project_name}_server/util/${project_name}_parameters.py"
mv "${project_name}_server/util/my_tool_steps.py" "${project_name}_server/util/${project_name}_steps.py"

# replace my_tool with project_name and MyTool with ProjectName
sed -i "s/my_tool/${project_name}/g" "${project_name}_server/model/${project_name}_model.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_server/model/${project_name}_model.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_server/project/${project_name}_server_project.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_server/project/${project_name}_server_project.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_server/serializer/${project_name}_serializers.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_server/serializer/${project_name}_serializers.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_server/util/${project_name}_algorithms.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_server/util/${project_name}_algorithms.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_server/util/${project_name}_parameters.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_server/util/${project_name}_parameters.py"

sed -i "s/my_tool/${project_name}/g" "${project_name}_server/util/${project_name}_steps.py"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_server/util/${project_name}_steps.py"
