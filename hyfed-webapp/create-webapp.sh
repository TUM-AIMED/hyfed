project_name="$1"

if [ -z "${project_name}" ]
then
  echo "Usage: ./create-webapp.sh project_name"
  exit
fi

echo "Creating project ${project_name} ..."

# Based on code from https://stackoverflow.com/questions/34420091/spinal-case-to-camel-case
ProjectName=$(echo "${project_name}" | sed -r 's/(^|_)(\w)/\U\2/g')

cp -r my_tool_webapp "${project_name}_webapp"

# replace my_tool with project_name
sed -i "s/my_tool/${project_name}/g" "${project_name}_webapp/karma.conf.js"
sed -i "s/my_tool/${project_name}/g" "${project_name}_webapp/package.json"
sed -i "s/my_tool/${project_name}/g" "${project_name}_webapp/package-lock.json"
sed -i "s/my_tool/${project_name}/g" "${project_name}_webapp/angular.json"
sed -i "s/my_tool/${project_name}/g" "${project_name}_webapp/Dockerfile"
sed -i "s/my_tool/${project_name}/g" "${project_name}_webapp/src/environments/environment.prod.ts"
sed -i "s/my_tool/${project_name}/g" "${project_name}_webapp/src/app/app.component.spec.ts"
sed -i "s/my_tool/${project_name}/g" "${project_name}_webapp/src/app/pages/about-page/about-page.component.html"


# replace MyTool with ProjectName
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/README.md"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/e2e/src/app.e2e-spec.ts"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/index.html"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/app/pages/index-page/index-page.component.html"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/app/pages/projects-page/projects-page.component.html"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/app/pages/about-page/about-page.component.html"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/app/pages/how-to-page/how-to-page.component.html"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/app/pages/account-page/account-page.component.html"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/app/app.component.html"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/app/app.component.spec.ts"
sed -i "s/MyTool/${ProjectName}/g" "${project_name}_webapp/src/app/models/project.model.ts"
