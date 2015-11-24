# Boardgame Piece Tracking App

This app allows you to keep track of the pieces of boardgames. This is a crowdsourced effort. Users may create, edit and delete their own boardgames. They may also create, edit, and delete pieces from boardgames. You may not edit or delete an item that is not yours.

## Pre-requisites
- Vagrant

## Build Information
1) Start by downloading the latest code from this repo.

2) From the repo, issue the command 'vagrant up'.

3) After the build complets, log into the node with 'vagrant ssh'.

4) 'cd /vagrant/catalog'

5) 'python database_setup.py'

6) 'python importbg.py'

7) 'python application.py'

8) From your browser, go to localhost:5000. Login and begin using the site.

## Author

LeoNineStudios@outlook.com

## License

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
License for the specific language governing permissions and limitations under
the License.
